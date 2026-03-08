# bgmd — Bible Gateway to Markdown

`bgmd` is a modern, Python-based CLI tool designed to fetch Bible passages from BibleGateway.com and convert them into clean, highly-structured Markdown. It is the successor to the legacy `bg2md` and `bg2obs-catholic` tools, optimized for use in note-taking apps like **Obsidian**.

## Features

- **Robust DOM Parsing:** Uses BeautifulSoup4 to surgically extract verse text, section headers, and metadata, avoiding the fragility of regex-based scrapers.
- **Obsidian Optimized:** Automatically generates YAML front matter, H6 verse markers (for CSS styling), and inline footnotes compatible with Obsidian's internal linking.
- **Local Caching:** Automatically stores fetched HTML in a local cache (`.bgmd_cache`) to minimize server hits and improve performance for repeated requests.
- **Advanced Fetching & Randomization:** Powered by `curl_cffi` with **browser impersonation rotation** and **request jitter** to mimic human behavior and bypass bot detection.
- **Catholic Canon Support:** Built-in support for the full Catholic canon (73 books), including Deuterocanonical books.
- **Flexible Translations:** Supports any translation available on Bible Gateway (e.g., NABRE, RSVCE, KJV, ESV).

## Installation

1. Ensure you have Python 3.11+ installed.
2. Install the required dependencies:
   ```bash
   pip install typer[all] curl-cffi beautifulsoup4 lxml rich
   ```

## Usage

### Fetching a Passage
Fetch a chapter using the default translation (NABRE):
```bash
python -m bgmd.cli fetch "John 3"
```

Fetch with a specific translation (e.g., RSVCE):
```bash
python -m bgmd.cli fetch "John 3" --translation RSVCE
```

### Listing Translations
Display a table of commonly used and recommended translations:
```bash
python -m bgmd.cli translations
```

### Options
- `-t, --translation`: Specify the Bible version (default: NABRE).
- `--no-cache`: Force a fresh fetch from Bible Gateway, ignoring the local cache.
- `--no-randomize`: Disable browser impersonation rotation (uses a fixed Chrome profile).
- `--no-jitter`: Disable randomized request delays.
- `-m, --mode`: Output format (`obsidian` or `plain`).
- `--debug`: Enable verbose logging and write debug HTML files.

## Caching & Randomization
`bgmd` is designed to be a "good citizen" when interacting with Bible Gateway:
- **Caching:** All fetched content is stored in the `.bgmd_cache/` directory. If you request a passage that has already been fetched, `bgmd` will load it from the disk instantly.
- **Randomization:** Every request rotates through a list of modern browser profiles (Chrome, Firefox, Safari, Edge) and includes a 0.5s–2.0s random delay to prevent pattern-based blocking.

## Project Structure
- `bgmd/models.py`: Data structures for verses, footnotes, and documents.
- `bgmd/fetcher.py`: Network logic using `curl_cffi`, impersonation rotation, and caching.
- `bgmd/parser.py`: HTML-to-Model conversion logic.
- `bgmd/formatter.py`: Model-to-Markdown formatting.
- `bgmd/canon.py`: Bible canon and book metadata management.
- `bgmd/translations.py`: Supported translation metadata.

## License
MIT
