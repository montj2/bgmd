# bgmd — Bible Gateway to Markdown

`bgmd` is a modern, Python-based CLI tool designed to fetch Bible passages from BibleGateway.com and convert them into clean, highly-structured Markdown. It is the successor to the legacy `bg2md` and `bg2obs-catholic` tools, optimized for use in note-taking apps like **Obsidian**.

## Features

- **Robust DOM Parsing:** Uses BeautifulSoup4 to surgically extract verse text, section headers, and metadata, avoiding the fragility of regex-based scrapers.
- **Obsidian Optimized:** Automatically generates YAML front matter, H6 verse markers (for CSS styling), and inline footnotes compatible with Obsidian's internal linking.
- **Daily Lectionary Support:** Integrated with the Vanderbilt Revised Common Lectionary to automatically fetch daily readings.
- **Global Caching:** Automatically stores fetched HTML in a centralized cache (`~/.cache/bgmd`) to minimize server hits and improve performance.
- **Advanced Fetching & Randomization:** Powered by `curl_cffi` with **browser impersonation rotation** and **request jitter** to mimic human behavior and bypass bot detection.
- **Catholic Canon Support:** Built-in support for the full Catholic canon (73 books), including Deuterocanonical books.
- **Flexible Translations:** Supports any translation available on Bible Gateway (e.g., NABRE, RSVCE, KJV, ESV).

## Installation & Usage with `uv`

The recommended way to run and manage `bgmd` is using [uv](https://github.com/astral-sh/uv).

### Global Installation
Install `bgmd` globally so you can run it from anywhere:
```bash
uv tool install .
```
Now you can simply run:
```bash
bgmd fetch "John 3"
```

### Run without installing (`uvx`)
Execute the tool directly from the source directory without permanent installation:
```bash
uvx --from . bgmd fetch "John 3"
```

### Development
If you prefer a traditional virtual environment:
```bash
pip install typer[all] curl-cffi beautifulsoup4 lxml rich icalendar
python -m bgmd.cli fetch "John 3"
```

## Usage

### Fetching a Passage
```bash
bgmd fetch "John 3:16-21"
```

### Comparing Translations
Compare multiple versions side-by-side:
```bash
bgmd compare "John 3:16" --translations "NABRE,RSVCE"
```
Or use a comma-separated list with the `fetch` command:
```bash
bgmd fetch "Psalm 23" -t "NABRE,KJV,RSVCE"
```

### Fetching Daily Readings
Fetch today's lectionary readings:
```bash
bgmd lectionary
```

Fetch readings for a specific date:
```bash
bgmd lectionary --date 2026-03-25
```

### Listing Translations
Display a table of commonly used and recommended translations:
```bash
bgmd translations
```

### Options
- `-t, --translation`: Specify the Bible version (default: NABRE).
- `--no-cache`: Force a fresh fetch from Bible Gateway, ignoring the local cache.
- `--no-randomize`: Disable browser impersonation rotation.
- `--no-jitter`: Disable randomized request delays.
- `-m, --mode`: Output format (`obsidian` or `plain`).
- `--debug`: Enable verbose logging.

## Documentation
`bgmd` includes a detailed man page. To view it:
```bash
man ./man/bgmd.1
```

## Caching & Randomization
`bgmd` is designed to be a "good citizen" when interacting with Bible Gateway:
- **Caching:** All fetched content is stored in `~/.cache/bgmd/`. Requests for the same passage are served instantly from disk.
- **Randomization:** Every request rotates through modern browser profiles (Chrome, Firefox, Safari, Edge) and includes a random delay to prevent pattern-based blocking.

## License
MIT
