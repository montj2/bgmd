import typer
import asyncio
from typing import List, Optional
from bgmd.canon import Canon
from bgmd.fetcher import Fetcher
from bgmd.parser import Parser
from bgmd.formatter import Formatter
from bgmd.translations import COMMON_TRANSLATIONS, get_translation
from rich import print
from rich.table import Table
import os

app = typer.Typer()

@app.command()
def fetch(
    reference: str,
    translation: str = typer.Option("NABRE", "--translation", "-t", help="Translation code (e.g. RSVCE, NABRE)"),
    canon_name: str = typer.Option("catholic", "--canon", help="Canon name"),
    mode: str = typer.Option("obsidian", "--mode", "-m", help="Output mode (obsidian, plain)"),
    no_cache: bool = typer.Option(False, "--no-cache", help="Skip local cache and fetch from network"),
    no_randomize: bool = typer.Option(False, "--no-randomize", help="Disable browser impersonation randomization"),
    no_jitter: bool = typer.Option(False, "--no-jitter", help="Disable randomized request delays"),
    debug: bool = typer.Option(False, "--debug", help="Enable debug output"),
    use_fixture: Optional[str] = typer.Option(None, "--fixture", help="Use a local HTML file instead of fetching"),
):
    """
    Fetch a Bible passage and output as Markdown.
    
    Example: bgmd fetch "John 3"
    """
    async def run_fetch():
        canon = Canon(canon_name)
        
        parts = reference.rsplit(' ', 1)
        if len(parts) < 2:
            print(f"[bold red]Error:[/bold red] Invalid reference '{reference}'. Expected 'Book Chapter'.")
            return
            
        book_name, chapter_str = parts
        book = canon.get_book(book_name)
        if not book:
            print(f"[bold red]Error:[/bold red] Book '{book_name}' not found in canon '{canon_name}'.")
            return
            
        try:
            chapter = int(chapter_str)
        except ValueError:
            print(f"[bold red]Error:[/bold red] Invalid chapter '{chapter_str}'.")
            return

        if use_fixture:
            if not os.path.exists(use_fixture):
                print(f"[bold red]Error:[/bold red] Fixture '{use_fixture}' not found.")
                return
            with open(use_fixture, 'r', encoding='utf-8') as f:
                html = f.read()
            if debug: print(f"Using fixture [bold blue]{use_fixture}[/bold blue]...")
        else:
            fetcher = Fetcher(translation)
            
            cache_path = fetcher._get_cache_path(book.bg_name, chapter)
            if not no_cache and cache_path.exists():
                if debug: print(f"Loading [bold blue]{book.display_name} {chapter}[/bold blue] from cache...")
            else:
                print(f"Fetching [bold green]{book.display_name} {chapter}[/bold green] ({translation})...")
            
            html = await fetcher.fetch_chapter(
                book.bg_name, 
                chapter, 
                use_cache=not no_cache,
                randomize=not no_randomize,
                jitter=not no_jitter
            )
        
        parser = Parser(book.display_name, chapter, translation)
        doc = parser.parse(html)
        
        if debug:
            print(f"Parsed {len(doc.verses)} verses, {len(doc.section_headers)} headers")

        formatter = Formatter(mode)
        output = formatter.format(doc)
        
        print(output)

    asyncio.run(run_fetch())

@app.command(name="translations")
def list_translations():
    """
    List commonly used Bible translations supported by this tool.
    """
    table = Table(title="Common Bible Translations")
    table.add_column("Code", style="cyan", no_wrap=True)
    table.add_column("Name", style="green")
    table.add_column("Language", style="magenta")
    table.add_column("Catholic", style="yellow")

    for t in COMMON_TRANSLATIONS:
        table.add_row(
            t.code,
            t.full_name,
            t.language,
            "Yes" if t.is_catholic else "No"
        )

    print(table)
    print("\n[italic]Note: Any translation code supported by BibleGateway can be used with the --translation flag.[/italic]")

if __name__ == "__main__":
    app()
