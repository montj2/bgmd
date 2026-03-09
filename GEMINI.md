# bgmd — Bible Gateway to Markdown

`bgmd` is a modern Python-based command-line tool designed to fetch Bible passages from BibleGateway.com and convert them into clean, highly-structured Markdown, specifically optimized for **Obsidian**.

## Project Overview

- **Purpose:** Successor to the legacy `bg2md` and `bg2obs-catholic` tools. It provides a unified, robust engine for scraping Bible passages and formatting them for digital note-taking.
- **Main Technologies:**
    - **Language:** Python 3.11+
    - **Fetching:** `curl_cffi` (with browser impersonation rotation).
    - **Parsing:** `BeautifulSoup4` (DOM-based parsing).
    - **CLI:** `Typer` & `Rich`.
- **Architecture (src layout):**
    - `src/bgmd/models.py`: Core data structures (`Verse`, `Footnote`, `PassageDoc`, `ComparisonDoc`).
    - `src/bgmd/fetcher.py`: Network requests with jitter and global caching (`~/.cache/bgmd/`).
    - `src/bgmd/parser.py`: Surgical DOM extraction logic (handles complex headers and verse ranges).
    - `src/bgmd/formatter.py`: Markdown generation (Obsidian, Plain, Table, Interleaved).
    - `src/bgmd/canon.py`: Bible book metadata loading via bundled CSV files.
    - `src/bgmd/psalms.py`: Automatic mapping between Masoretic and Vulgate/LXX Psalm numbering.
    - `src/bgmd/lectionary.py`: Integration with Vanderbilt Revised Common Lectionary (ICS + Web scraping).
    - `src/bgmd/config.py`: Persistent user settings (`~/.config/bgmd/config.json`).

## Building and Running

### Installation
The project uses `uv` for dependency management and distribution.
```bash
# Global install
uv tool install .

# Local development
uv sync
```

### Key Commands
- **Fetch a passage:** `bgmd fetch "John 3"`
- **Compare translations:** `bgmd compare "John 3:16" -t "NABRE,RSVCE"`
- **Fetch lectionary:** `bgmd lectionary --translation "DRA,RSVCE"`
- **Configure defaults:** `bgmd config-set translation RSVCE`
- **View documentation:** `man ./man/bgmd.1`

## Development Conventions

- **Caching:** HTML is stored in `~/.cache/bgmd/`. Use `--no-cache` only when necessary.
- **Psalm Mapping:** By default, the tool maps standard Psalm numbers to the traditional numbering for `DRA` and `VULGATE`. Disable with `--no-psalm-map`.
- **Parsing Logic:**
    - Reliable markers: `span` with class `text` and IDs starting with `en-`.
    - Verse identification: Priority given to `.versenum` and `.chapternum` (first verse).
    - Whitespace: Aggressively normalized to single spaces for Markdown table compatibility.
- **Obsidian Formatting:** 
    - Verse numbers: `###### v` (H6).
    - Footnotes: Inline `^[]` format.
    - Front matter: Comprehensive YAML metadata.
- **Packaging:** Uses `src` layout. All data files in `src/bgmd/books/` must be included via `pyproject.toml`.
