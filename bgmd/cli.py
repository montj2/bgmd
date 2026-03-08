import typer
import asyncio
import re
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

def parse_reference(ref: str):
    """
    Parses a reference string like "John 3", "John 3:16", or "John 3:16-21".
    Returns (book_name, chapter, start_verse, end_verse)
    """
    # Regex to handle various formats
    # 1. Book (can have spaces/numbers)
    # 2. Chapter
    # 3. Verse range (optional)
    pattern = r'^(.+?)\s+(\d+)(?::(\d+)(?:-(\d+))?)?$'
    match = re.match(pattern, ref.strip())
    if not match:
        return None
    
    book = match.group(1).strip()
    chapter = int(match.group(2))
    start_v = int(match.group(3)) if match.group(3) else None
    end_v = int(match.group(4)) if match.group(4) else start_v
    
    return book, chapter, start_v, end_v

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
    
    Example: bgmd fetch "John 3:16-21"
    """
    async def run_fetch():
        canon = Canon(canon_name)
        
        parsed = parse_reference(reference)
        if not parsed:
            print(f"[bold red]Error:[/bold red] Invalid reference format '{reference}'. Expected 'Book Chapter' or 'Book Chapter:Verse-Range'.")
            return
            
        book_name, chapter, start_v, end_v = parsed
        book = canon.get_book(book_name)
        if not book:
            print(f"[bold red]Error:[/bold red] Book '{book_name}' not found in canon '{canon_name}'.")
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
            # Check cache location
            cache_path = fetcher._get_cache_path(book.bg_name, chapter, start_v, end_v)
            if not no_cache and cache_path.exists():
                if debug: print(f"Loading from cache: {cache_path}")
            else:
                # Also check full chapter cache
                full_path = fetcher._get_cache_path(book.bg_name, chapter)
                if not no_cache and full_path.exists():
                    if debug: print(f"Loading full chapter from cache: {full_path}")
                else:
                    print(f"Fetching [bold green]{book.display_name} {chapter}{f':{start_v}' if start_v else ''}{f'-{end_v}' if end_v and end_v != start_v else ''}[/bold green] ({translation})...")
            
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
