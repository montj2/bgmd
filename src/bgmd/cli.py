import typer
import asyncio
import re
from datetime import date as date_obj
from typing import List, Optional
from bgmd.canon import Canon
from bgmd.fetcher import Fetcher
from bgmd.parser import Parser
from bgmd.formatter import Formatter
from bgmd.translations import COMMON_TRANSLATIONS, get_translation
from bgmd.lectionary import get_provider
from bgmd.config import config
from bgmd.models import ComparisonDoc, PassageDoc
from bgmd.psalms import VULGATE_NUMBERED_VERSIONS, map_mt_to_vulgate
from rich.console import Console
from rich.table import Table
from pathlib import Path
import os
import sys

app = typer.Typer()
console = Console(highlight=False, soft_wrap=True)

def parse_reference(ref: str):
    # Support "2 Kings 5:1-15ab", "Psalm 42:2, 3"
    match = re.match(r'^([1-3]?\s*[a-zA-Z\s]+?)\s*(\d+.*)$', ref.strip())
    if not match:
        return None
    
    book_name = match.group(1).strip()
    rest = match.group(2).strip()
    
    # Extract chapter
    chapter_match = re.match(r'^(\d+)', rest)
    if not chapter_match:
        return None
    chapter = int(chapter_match.group(1))
    
    # Heuristic for labels
    start_v = None
    end_v = None
    
    verse_part_match = re.search(r':(\d+)', rest)
    if verse_part_match:
        start_v = int(verse_part_match.group(1))
        # Hyphenated range
        end_match = re.search(r'-(\d+)', rest)
        if end_match:
            end_v = int(end_match.group(1))
        # Comma separated
        elif ',' in rest:
            # For commas, we don't have a single end_v. 
            # We'll set end_v to None to signal a complex range to the fetcher
            end_v = None
        else:
            end_v = start_v
            
    return book_name, chapter, start_v, end_v, rest

async def _fetch_doc(
    reference: str,
    translation: str,
    canon_name: str,
    no_cache: bool,
    no_randomize: bool,
    no_jitter: bool,
    debug: bool,
    no_psalm_map: bool = False
) -> Optional[PassageDoc]:
    canon = Canon(canon_name)
    parsed = parse_reference(reference)
    if not parsed:
        console.print(f"[bold red]Error:[/bold red] Invalid reference format '{reference}'.")
        return None
        
    book_name, chapter, start_v, end_v, raw_rest = parsed
    book = canon.get_book(book_name)
    if not book:
        console.print(f"[bold red]Error:[/bold red] Book '{book_name}' not found.")
        return None

    actual_chapter = chapter
    actual_start_v = start_v
    actual_end_v = end_v
    
    # Determine the search string for BibleGateway
    # If it's a simple chapter:book, use our existing logic
    # If it has commas or suffixes, we might want to be more careful.
    
    # Check if we need Psalm mapping
    if book.slug == "psalms" and translation.upper() in VULGATE_NUMBERED_VERSIONS and not no_psalm_map:
        mapped_ch, mapped_start, mapped_end, note = map_mt_to_vulgate(chapter, start_v, end_v)
        if mapped_ch != chapter or note:
            if not debug:
                msg = f"[cyan]Mapping {book.display_name} {chapter}"
                if start_v: msg += f":{start_v}"
                msg += f" -> {book.display_name} {mapped_ch}"
                if mapped_start: msg += f":{mapped_start}"
                msg += f" for {translation}[/cyan]"
                console.print(msg)
                if note: console.print(f"[italic]{note}[/italic]")
            
            actual_chapter = mapped_ch
            # Adjust the raw_rest for the mapped chapter
            raw_rest = re.sub(r'^\d+', str(actual_chapter), raw_rest)
            actual_start_v = mapped_start
            actual_end_v = mapped_end

    cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
    fetcher = Fetcher(translation, cache_dir=cache_dir)
    
    # New logic: if end_v is None but there was a start_v, it's a complex range.
    # We'll pass the full book name + raw_rest to fetch_reference.
    if start_v is not None and end_v is None:
        # Complex range (e.g. "42:2, 3")
        # We need a new method in fetcher or update existing one
        html = await fetcher.fetch_reference(
            book.bg_name, 
            actual_chapter, 
            raw_rest=raw_rest, # Pass the raw string
            use_cache=not no_cache,
            randomize=not no_randomize,
            jitter=not no_jitter
        )
    else:
        html = await fetcher.fetch_reference(
            book.bg_name, 
            actual_chapter, 
            actual_start_v, 
            actual_end_v,
            use_cache=not no_cache,
            randomize=not no_randomize,
            jitter=not no_jitter
        )
    
    parser = Parser(book.display_name, chapter, translation, start_verse=start_v, end_verse=end_v)
    return parser.parse(html)

async def _fetch_and_format(
    reference: str,
    translation: str,
    canon_name: str,
    mode: str,
    no_cache: bool,
    no_randomize: bool,
    no_jitter: bool,
    debug: bool,
    no_psalm_map: bool = False
) -> Optional[str]:
    doc = await _fetch_doc(reference, translation, canon_name, no_cache, no_randomize, no_jitter, debug, no_psalm_map)
    if not doc:
        return None
    formatter = Formatter(mode)
    return formatter.format(doc)

@app.command()
def fetch(
    reference: str,
    translation: str = typer.Option(config.settings.translation, "--translation", "-t", help="Translation code(s)"),
    canon_name: str = typer.Option(config.settings.canon, "--canon", help="Canon name"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m", help="Output mode"),
    layout: str = typer.Option("table", "--layout", "-l", help="Comparison layout"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip local cache"),
    no_randomize: bool = typer.Option(config.settings.no_randomize, "--no-randomize"),
    no_jitter: bool = typer.Option(config.settings.no_jitter, "--no-jitter"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch a Bible passage."""
    async def run():
        if ',' in translation:
            translations = [t.strip() for t in translation.split(',')]
            docs = []
            for t in translations:
                doc = await _fetch_doc(reference, t, canon_name, no_cache, no_randomize, no_jitter, debug, no_psalm_map)
                if doc: docs.append(doc)
            if docs:
                comp = ComparisonDoc(reference=reference, translations=[d.translation for d in docs], docs=docs)
                output = Formatter(mode).format_comparison(comp, layout=layout)
                sys.stdout.write(output + "\n")
        else:
            output = await _fetch_and_format(reference, translation, canon_name, mode, no_cache, no_randomize, no_jitter, debug, no_psalm_map)
            if output: sys.stdout.write(output + "\n")

    asyncio.run(run())

@app.command()
def compare(
    reference: str,
    translations: str = typer.Option(config.settings.translation, "--translations", "-t"),
    layout: str = typer.Option("table", "--layout", "-l"),
    canon_name: str = typer.Option(config.settings.canon, "--canon"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Compare multiple translations side-by-side."""
    async def run():
        trans_list = [t.strip() for t in translations.split(',')]
        docs = []
        for t in trans_list:
            doc = await _fetch_doc(reference, t, canon_name, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_psalm_map)
            if doc: docs.append(doc)
        if docs:
            comp = ComparisonDoc(reference=reference, translations=[d.translation for d in docs], docs=docs)
            output = Formatter().format_comparison(comp, layout=layout)
            sys.stdout.write(output + "\n")

    asyncio.run(run())

@app.command()
def lectionary(
    date: str = typer.Option(None, "--date", help="Target date (YYYY-MM-DD)"),
    translation: str = typer.Option(config.settings.translation, "--translation", "-t"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m"),
    layout: str = typer.Option("table", "--layout", "-l"),
    source: str = typer.Option(config.settings.lectionary_source, "--source", "-s", help="Lectionary source (usccb, vanderbilt)"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Fetch daily lectionary readings for a given date."""
    async def run():
        target_date = date_obj.fromisoformat(date) if date else date_obj.today()
        cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
        provider = get_provider(source, cache_dir=cache_dir)
        
        console.print(f"Loading lectionary ([bold cyan]{source}[/bold cyan]) for [bold cyan]{target_date}[/bold cyan]...")
        summary, refs = await provider.get_readings(target_date)
        
        if not refs:
            console.print(f"[yellow]No readings found for {target_date} ({summary}).[/yellow]")
            return

        console.print(f"Readings for [bold green]{summary}[/bold green]:")
        for ref in refs:
            print(f"  - {ref}")
        console.print("-" * 20)

        is_comparison = ',' in translation
        trans_list = [t.strip() for t in translation.split(',')] if is_comparison else [translation]

        for ref in refs:
            console.print(f"\n[bold blue]>>> {ref}[/bold blue]")
            if is_comparison:
                docs = []
                for t in trans_list:
                    doc = await _fetch_doc(ref, t, config.settings.canon, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_psalm_map)
                    if doc: docs.append(doc)
                if docs:
                    comp = ComparisonDoc(reference=ref, translations=[d.translation for d in docs], docs=docs)
                    sys.stdout.write(Formatter(mode).format_comparison(comp, layout=layout) + "\n")
            else:
                output = await _fetch_and_format(ref, translation, config.settings.canon, mode, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_psalm_map)
                if output:
                    sys.stdout.write(output + "\n")
            
            console.print("\n" + "="*40 + "\n")

    asyncio.run(run())

@app.command()
def config_show():
    """Show current settings."""
    table = Table(title="bgmd Settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    for k, v in config.get_all().items():
        table.add_row(k, str(v))
    console.print(table)
    console.print(f"\nConfig file: [italic]{config.config_path}[/italic]")

@app.command()
def config_set(key: str, value: str):
    """Set a configuration value."""
    try:
        if value.lower() in ["true", "1", "yes"]:
            typed_value = True
        elif value.lower() in ["false", "0", "no"]:
            typed_value = False
        else:
            typed_value = value
            
        config.set(key, typed_value)
        console.print(f"[bold green]Updated {key} to {value}[/bold green]")
    except KeyError as e:
        console.print(f"[bold red]{e}[/bold red]")

@app.command(name="translations")
def list_translations():
    """List commonly used Bible translations."""
    table = Table(title="Common Bible Translations")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="green")
    for t in COMMON_TRANSLATIONS:
        table.add_row(t.code, t.full_name)
    console.print(table)

if __name__ == "__main__":
    app()
