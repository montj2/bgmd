import typer
import asyncio
import re
from datetime import date as date_obj
from typing import List, Optional, Tuple, Set
from bgmd.canon import Canon
from bgmd.fetcher import Fetcher
from bgmd.parser import Parser
from bgmd.formatter import Formatter
from bgmd.translations import COMMON_TRANSLATIONS, get_translation
from bgmd.lectionary import get_provider
from bgmd.config import config
from bgmd.models import ComparisonDoc, PassageDoc
from bgmd.mapping import map_reference
from rich.console import Console
from rich.table import Table
from pathlib import Path
import os
import sys

app = typer.Typer()
console = Console(highlight=False, soft_wrap=True)

def parse_reference(ref: str):
    match = re.match(r'^([1-3]?\s*[a-zA-Z\s]+?)\s*(\d+.*)$', ref.strip())
    if not match:
        return None
    
    book_name = match.group(1).strip()
    rest = match.group(2).strip()
    
    chapter_match = re.match(r'^(\d+)', rest)
    if not chapter_match:
        return None
    chapter = int(chapter_match.group(1))
    
    start_v = None
    end_v = None
    requested_verses: Set[int] = set()
    
    if ':' in rest:
        v_part = rest.split(':', 1)[1]
        v_part = v_part.replace(' and ', ', ')
        fragments = [f.strip() for f in v_part.split(',')]
        
        for frag in fragments:
            clean_frag = re.sub(r'[a-z]+', '', frag).strip()
            if '-' in clean_frag:
                try:
                    s, e = map(int, clean_frag.split('-', 1))
                    for i in range(s, e + 1):
                        requested_verses.add(i)
                    if start_v is None or s < start_v: start_v = s
                    if end_v is None or e > end_v: end_v = e
                except ValueError:
                    pass
            elif clean_frag:
                try:
                    val = int(clean_frag)
                    requested_verses.add(val)
                    if start_v is None or val < start_v: start_v = val
                    if end_v is None or val > end_v: end_v = val
                except ValueError:
                    pass
                    
    return book_name, chapter, start_v, end_v, rest, requested_verses

async def _fetch_doc(
    reference: str,
    translation: str,
    canon_name: str,
    no_cache: bool,
    no_randomize: bool,
    no_jitter: bool,
    debug: bool,
    no_map: bool = False,
    is_usccb: bool = False
) -> Optional[PassageDoc]:
    canon = Canon(canon_name)
    parsed = parse_reference(reference)
    if not parsed:
        console.print(f"[bold red]Error:[/bold red] Invalid reference format '{reference}'.")
        return None
        
    book_name, chapter, start_v, end_v, raw_rest, requested_verses = parsed
    book = canon.get_book(book_name)
    if not book:
        console.print(f"[bold red]Error:[/bold red] Book '{book_name}' not found.")
        return None

    actual_chapter = chapter
    actual_verses = requested_verses
    
    if not no_map:
        mapped_ch, mapped_verses, note = map_reference(book.slug, chapter, requested_verses, translation, is_usccb=is_usccb)
        if mapped_ch != chapter or mapped_verses != requested_verses:
            if not debug:
                msg = f"[cyan]Mapping {book.display_name} {chapter}"
                if requested_verses: msg += f" (verses {sorted(list(requested_verses))})"
                msg += f" -> {book.display_name} {mapped_ch}"
                if mapped_verses: msg += f" (verses {sorted(list(mapped_verses))})"
                msg += f" for {translation}[/cyan]"
                console.print(msg)
                if note: console.print(f"[italic]{note}[/italic]")
            
            actual_chapter = mapped_ch
            actual_verses = mapped_verses

    cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
    fetcher = Fetcher(translation, cache_dir=cache_dir)
    
    if actual_verses or ',' in raw_rest:
        html = await fetcher.fetch_chapter(book.bg_name, actual_chapter, use_cache=not no_cache, randomize=not no_randomize, jitter=not no_jitter)
    else:
        html = await fetcher.fetch_reference(
            book.bg_name, 
            actual_chapter, 
            start_v, 
            end_v,
            use_cache=not no_cache,
            randomize=not no_randomize,
            jitter=not no_jitter
        )
    
    parser = Parser(book.display_name, chapter, translation, start_verse=start_v, end_verse=end_v, requested_verses=actual_verses)
    doc = parser.parse(html)
    
    if actual_verses != requested_verses and len(actual_verses) == len(requested_verses):
        v_map = dict(zip(sorted(list(actual_verses)), sorted(list(requested_verses))))
        for v in doc.verses:
            if v.number in v_map:
                v.number = v_map[v.number]
                
    return doc

async def _fetch_and_format(
    reference: str,
    translation: str,
    canon_name: str,
    mode: str,
    no_cache: bool,
    no_randomize: bool,
    no_jitter: bool,
    debug: bool,
    no_map: bool = False,
    is_usccb: bool = False
) -> Optional[str]:
    doc = await _fetch_doc(reference, translation, canon_name, no_cache, no_randomize, no_jitter, debug, no_map, is_usccb)
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
    no_map: bool = typer.Option(False, "--no-map", help="Disable automatic numbering mapping"),
    debug: bool = typer.Option(False, "--debug"),
):
    """Fetch a Bible passage."""
    async def run():
        if ',' in translation:
            translations = [t.strip() for t in translation.split(',')]
            docs = []
            for t in translations:
                doc = await _fetch_doc(reference, t, canon_name, no_cache, no_randomize, no_jitter, debug, no_map)
                if doc: docs.append(doc)
            if docs:
                comp = ComparisonDoc(reference=reference, translations=[d.translation for d in docs], docs=docs)
                output = Formatter(mode).format_comparison(comp, layout=layout)
                sys.stdout.write(output + "\n")
        else:
            output = await _fetch_and_format(reference, translation, canon_name, mode, no_cache, no_randomize, no_jitter, debug, no_map)
            if output: sys.stdout.write(output + "\n")

    asyncio.run(run())

@app.command()
def compare(
    reference: str,
    translations: str = typer.Option(config.settings.translation, "--translations", "-t"),
    layout: str = typer.Option("table", "--layout", "-l"),
    canon_name: str = typer.Option(config.settings.canon, "--canon"),
    no_map: bool = typer.Option(False, "--no-map"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Compare multiple translations side-by-side."""
    async def run():
        trans_list = [t.strip() for t in translations.split(',')]
        docs = []
        for t in trans_list:
            doc = await _fetch_doc(reference, t, canon_name, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_map)
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
    no_map: bool = typer.Option(False, "--no-map"),
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
        is_usccb = source.lower() == "usccb"

        for ref in refs:
            console.print(f"\n[bold blue]>>> {ref}[/bold blue]")
            if is_comparison:
                docs = []
                for t in trans_list:
                    doc = await _fetch_doc(ref, t, config.settings.canon, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_map, is_usccb=is_usccb)
                    if doc: docs.append(doc)
                if docs:
                    comp = ComparisonDoc(reference=ref, translations=[d.translation for d in docs], docs=docs)
                    sys.stdout.write(Formatter(mode).format_comparison(comp, layout=layout) + "\n")
            else:
                output = await _fetch_and_format(ref, translation, config.settings.canon, mode, no_cache, config.settings.no_randomize, config.settings.no_jitter, False, no_map, is_usccb=is_usccb)
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
