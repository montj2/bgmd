# bgmd — Bible Gateway to Markdown

`bgmd` is a modern Python-based command-line tool designed to fetch Bible passages from BibleGateway.com and convert them into clean, highly-structured Markdown, specifically optimized for **Obsidian**.

## Project Overview

- **Purpose:** Successor to the legacy `bg2md` and `bg2obs-catholic` tools. It provides a unified, robust engine for scraping Bible passages and formatting them for digital note-taking.
- **Main Technologies:**
    - **Language:** Python 3.11+
    - **Fetching:** `curl_cffi` (with browser impersonation to bypass bot detection).
    - **Parsing:** `BeautifulSoup4` (DOM-based parsing for stability).
    - **CLI:** `Typer` & `Rich` (for a modern, user-friendly terminal experience).
- **Architecture:**
    - `bgmd/models.py`: Defines the core data structures (`Verse`, `Footnote`, `PassageDoc`).
    - `bgmd/fetcher.py`: Manages network requests and local caching of raw HTML.
    - `bgmd/parser.py`: Implements surgical DOM extraction logic.
    - `bgmd/formatter.py`: Converts parsed models into Obsidian-ready Markdown.
    - `bgmd/canon.py` & `bgmd/translations.py`: Manage Bible book metadata and translation mappings.

## Building and Running

### Installation
Ensure you have Python 3.11+ and install dependencies:
```bash
pip install typer[all] curl-cffi beautifulsoup4 lxml rich
```

### Key Commands
- **Fetch a passage:**
  ```bash
  python -m bgmd.cli fetch "John 3"
  ```
- **Fetch with specific translation:**
  ```bash
  python -m bgmd.cli fetch "John 3" --translation RSVCE
  ```
- **Compare translations:**
  ```bash
  python -m bgmd.cli compare "John 3:16" --translations "NABRE,RSVCE"
  ```
- **List supported translations:**
  ```bash
  python -m bgmd.cli translations
  ```
- **View man page:**
  ```bash
  man ./man/bgmd.1
  ```
- **Bypass cache:**
  ```bash
  python -m bgmd.cli fetch "John 3" --no-cache
  ```

## Development Conventions

- **Caching:** The tool is conservative with server requests. All fetched HTML is stored in `.bgmd_cache/`. Use `--no-cache` only when necessary.
- **Parsing Logic:** The parser prioritizes `span` elements with IDs starting with `en-` as these are the most reliable markers for verse content across Bible Gateway's evolving UI.
- **Obsidian Formatting:** 
    - Verse numbers are formatted as `###### v` (H6).
    - Footnotes are converted to inline `^[]` format.
    - YAML front matter is included for metadata.
- **Dependencies:** Avoid adding new dependencies unless absolutely necessary for core functionality. Prefer standard library or well-established libraries like `BeautifulSoup4`.
