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
from rich import print
from rich.table import Table
from pathlib import Path
import os

app = typer.Typer()

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

async def _fetch_and_format(
    reference: str,
    translation: str,
    canon_name: str,
    mode: str,
    no_cache: bool,
    no_randomize: bool,
    no_jitter: bool,
    debug: bool
) -> Optional[str]:
    canon = Canon(canon_name)
    parsed = parse_reference(reference)
    if not parsed:
        print(f"[bold red]Error:[/bold red] Invalid reference format '{reference}'.")
        return None
        
    book_name, chapter, start_v, end_v = parsed
    book = canon.get_book(book_name)
    if not book:
        print(f"[bold red]Error:[/bold red] Book '{book_name}' not found.")
        return None

    # Respect custom cache dir if set
    cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
    fetcher = Fetcher(translation, cache_dir=cache_dir)
    
    html = await fetcher.fetch_reference(
        book.bg_name, 
        chapter, 
        start_v, 
        end_v,
        use_cache=not no_cache,
        randomize=not no_randomize,
        jitter=not no_jitter
    )
    
    parser = Parser(book.display_name, chapter, translation, start_verse=start_v, end_verse=end_v)
    doc = parser.parse(html)
    
    formatter = Formatter(mode)
    return formatter.format(doc)

@app.command()
def fetch(
    reference: str,
    translation: str = typer.Option(config.settings.translation, "--translation", "-t", help="Translation code"),
    canon_name: str = typer.Option(config.settings.canon, "--canon", help="Canon name"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m", help="Output mode"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip local cache"),
    no_randomize: bool = typer.Option(config.settings.no_randomize, "--no-randomize", help="Disable randomization"),
    no_jitter: bool = typer.Option(config.settings.no_jitter, "--no-jitter", help="Disable delay"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
):
    """Fetch a Bible passage."""
    async def run():
        output = await _fetch_and_format(reference, translation, canon_name, mode, no_cache, no_randomize, no_jitter, debug)
        if output: print(output)

    asyncio.run(run())

@app.command()
def lectionary(
    date: str = typer.Option(None, "--date", help="Target date (YYYY-MM-DD), defaults to today"),
    translation: str = typer.Option(config.settings.translation, "--translation", "-t"),
    mode: str = typer.Option(config.settings.mode, "--mode", "-m"),
    no_cache: bool = typer.Option(False, "--no-cache"),
):
    """Fetch daily lectionary readings for a given date."""
    async def run():
        target_date = date_obj.fromisoformat(date) if date else date_obj.today()
        cache_dir = Path(config.settings.cache_dir) if config.settings.cache_dir else None
        provider = LectionaryProvider(cache_dir=cache_dir)
        
        print(f"Loading lectionary for [bold cyan]{target_date}[/bold cyan]...")
        summary, refs = await provider.get_readings(target_date)
        
        if not refs:
            print(f"[yellow]No readings found for {target_date} ({summary}).[/yellow]")
            return

        print(f"Readings for [bold green]{summary}[/bold green]:")
        for ref in refs:
            print(f"  - {ref}")
        print("-" * 20)

        for ref in refs:
            print(f"\n[bold blue]>>> {ref}[/bold blue]")
            output = await _fetch_and_format(ref, translation, config.settings.canon, mode, no_cache, config.settings.no_randomize, config.settings.no_jitter, False)
            if output:
                print(output)
                print("\n" + "="*40 + "\n")

    asyncio.run(run())

@app.command()
def config_show():
    """Show current settings."""
    table = Table(title="bgmd Settings")
    table.add_column("Key", style="cyan")
    table.add_column("Value", style="green")
    for k, v in config.get_all().items():
        table.add_row(k, str(v))
    print(table)
    print(f"\nConfig file: [italic]{config.config_path}[/italic]")

@app.command()
def config_set(key: str, value: str):
    """Set a configuration value."""
    try:
        # Handle boolean strings
        if value.lower() in ["true", "1", "yes"]:
            typed_value = True
        elif value.lower() in ["false", "0", "no"]:
            typed_value = False
        else:
            typed_value = value
            
        config.set(key, typed_value)
        print(f"[bold green]Updated {key} to {value}[/bold green]")
    except KeyError as e:
        print(f"[bold red]{e}[/bold red]")

@app.command(name="translations")
def list_translations():
    """List commonly used Bible translations."""
    table = Table(title="Common Bible Translations")
    table.add_column("Code", style="cyan")
    table.add_column("Name", style="green")
    for t in COMMON_TRANSLATIONS:
        table.add_row(t.code, t.full_name)
    print(table)

if __name__ == "__main__":
    app()
