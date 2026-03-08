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
from bgmd.lectionary import LectionaryProvider
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
    pattern = r'^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$'
    match = re.match(pattern, ref.strip())
    if not match:
        return None
    
    book = match.group(1).strip()
    chapter = int(match.group(2))
    start_v = int(match.group(3)) if match.group(3) else None
    end_v = int(match.group(4)) if match.group(4) else start_v
    
    return book, chapter, start_v, end_v

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
        
    book_name, chapter, start_v, end_v = parsed
    book = canon.get_book(book_name)
    if not book:
        console.print(f"[bold red]Error:[/bold red] Book '{book_name}' not found.")
        return None

    # Psalm Mapping
    actual_chapter = chapter
    actual_start_v = start_v
    actual_end_v = end_v
    if book.slug == "psalms" and translation.upper() in VULGATE_NUMBERED_VERSIONS and not no_psalm_map:
        mapped_ch, mapped_start, mapped_end, note = map_mt_to_vulgate(chapter, start_v, end_v)
        if mapped_ch != chapter or note:
            if not debug: # Don't double print if debug is on
                msg = f"[cyan]Mapping {book.display_name} {chapter}"
                if start_v: msg += f":{start_v}"
                msg += f" -> {book.display_name} {mapped_ch}"
                if mapped_start: msg += f":{mapped_start}"
                msg += f" for {translation}[/cyan]"
                console.print(msg)
                if note: console.print(f"[italic]{note}[/italic]")
            
            actual_chapter = mapped_ch
            actual_start_v = mapped_start
            actual_end_v = mapped_end

    cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
    fetcher = Fetcher(translation, cache_dir=cache_dir)
    
    html = await fetcher.fetch_reference(
        book.bg_name, 
        actual_chapter, 
        actual_start_v, 
        actual_end_v,
        use_cache=not no_cache,
        randomize=not no_randomize,
        jitter=not no_jitter
    )
    
    # We pass the ORIGINAL reference info to the parser so the output Markdown
    # labels it as requested (e.g. "Psalm 23") but uses the "mapped" content.
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
    translation: str = typer.Option(config.settings.translation, "--translation", "-t", help="Translation code(s), comma-separated for comparison"),
    canon_name: str = typer.Option(config.settings.canon, "--canon", help="Canon name"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m", help="Output mode (obsidian, plain)"),
    layout: str = typer.Option("table", "--layout", "-l", help="Comparison layout (table, interleaved)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip local cache"),
    no_randomize: bool = typer.Option(config.settings.no_randomize, "--no-randomize", help="Disable randomization"),
    no_jitter: bool = typer.Option(config.settings.no_jitter, "--no-jitter", help="Disable delay"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map", help="Disable automatic Psalm numbering mapping for Vulgate versions"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
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
    translations: str = typer.Option(config.settings.translation, "--translations", "-t", help="Comma-separated translation codes"),
    layout: str = typer.Option("table", "--layout", "-l", help="Layout (table, interleaved)"),
    canon_name: str = typer.Option(config.settings.canon, "--canon"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map", help="Disable automatic Psalm mapping"),
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
    date: str = typer.Option(None, "--date", help="Target date (YYYY-MM-DD), defaults to today"),
    translation: str = typer.Option(config.settings.translation, "--translation", "-t", help="Translation code(s), comma-separated for comparison"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m"),
    layout: str = typer.Option("table", "--layout", "-l", help="Comparison layout (table, interleaved)"),
    no_psalm_map: bool = typer.Option(False, "--no-psalm-map", help="Disable automatic Psalm mapping"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Fetch daily lectionary readings for a given date."""
    async def run():
        target_date = date_obj.fromisoformat(date) if date else date_obj.today()
        cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
        provider = LectionaryProvider(cache_dir=cache_dir)
        
        console.print(f"Loading lectionary for [bold cyan]{target_date}[/bold cyan]...")
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
