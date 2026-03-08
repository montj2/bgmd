# bgmd — Bible Gateway to Markdown: Project Specification

**Version:** 0.1 — Draft  
**Scope:** Successor to `bg2md` + `bg2obs-catholic`. Single unified tool.  
**Status:** Pre-implementation

---

## 1. Goals

Replace the Ruby + Bash + Perl tri-tool stack with a single, maintainable CLI that:

- Fetches any scope of Scripture (verse, range, chapter, book, full Bible) from BibleGateway
- Outputs clean, structured Markdown optimized for Obsidian but not coupled to it
- Supports the full Catholic canon (Deuterocanonicals included)
- Preserves footnotes, cross-references, and headings as first-class content
- Is distributable, portable, and packageable (Debian `.deb`, PyPI, Homebrew)

Non-goals (out of scope for v1):
- Bible Gateway authentication / subscriber-only features
- Offline Bible text bundling (legal/licensing concern)
- Obsidian plugin packaging

---

## 2. Language Decision: Python

**Recommendation: Python 3.11+**

| Factor | Python | Go |
|---|---|---|
| HTML parsing maturity | ✅ BeautifulSoup + lxml | ⚠️ goquery (good, not great) |
| Text transformation ergonomics | ✅ Strong | Adequate |
| Async HTTP (parallel chapter fetch) | ✅ httpx + asyncio | ✅ net/http goroutines |
| CLI ecosystem | ✅ Typer (Pydantic-backed) | ✅ Cobra |
| Distribution (single binary) | ❌ PyInstaller is messy | ✅ Native |
| Debian packaging | ✅ dh-python, well-trodden | ✅ Also viable |
| Iteration speed | ✅ Faster | Slower |
| Runtime dependency | Python 3.11+ | None |

Go's single-binary advantage matters for distribution. Python wins on everything else for a text-processing tool. Decision: **Python**, with a `pyproject.toml`-based layout for PyPI and `debian/` directory for `.deb` packaging.

If a static binary becomes a hard requirement later, the architecture below is clean enough to port.

---

## 3. Architecture

```
┌─────────┐     ┌──────────┐     ┌─────────────┐     ┌───────────┐     ┌────────┐
│   CLI   │────▶│ Resolver │────▶│   Fetcher   │────▶│  Parser   │────▶│ Writer │
│ (Typer) │     │          │     │(curl_cffi)  │     │(BeautifulS│     │        │
└─────────┘     └──────────┘     └─────────────┘     └───────────┘     └────────┘
                     │                  │                   │
               Expands "John"     Rate-limited,        Produces
               to ch 1–21         cached, retried      PassageDoc
               per canon          to disk              model
```

### 3.1 Modules

| Module | Responsibility |
|---|---|
| `bgmd.cli` | Entry point. Typer app. Argument parsing, output routing. |
| `bgmd.resolver` | Expands a reference string into a list of fetch targets. Canon-aware. |
| `bgmd.canon` | Canon registry (Catholic, Protestant, Orthodox). Book lists + chapter counts. |
| `bgmd.fetcher` | Async HTTP fetch with rate limiting, retry (exp. backoff), disk cache. |
| `bgmd.parser` | BeautifulSoup-based HTML → `PassageDoc`. Replaces all regex scraping. |
| `bgmd.formatter` | `PassageDoc` → Markdown string. Configurable output style. |
| `bgmd.writer` | File/directory creation, naming conventions, YAML front matter. |
| `bgmd.models` | Dataclasses: `PassageDoc`, `Verse`, `Footnote`, `CrossRef`, `SectionHeader`. |

---

## 4. Data Model

```python
@dataclass
class Verse:
    number: int
    text: str
    footnote_refs: list[str]        # e.g. ["a", "b"]
    crossref_refs: list[str]

@dataclass
class Footnote:
    label: str                      # "a", "b", etc.
    text: str

@dataclass
class CrossRef:
    label: str
    targets: list[str]              # e.g. ["Jn 1:1", "Gen 1:1"]

@dataclass
class SectionHeader:
    before_verse: int
    text: str

@dataclass
class PassageDoc:
    book: str
    chapter: int
    translation: str
    verses: list[Verse]
    section_headers: list[SectionHeader]
    footnotes: list[Footnote]
    crossrefs: list[CrossRef]
    copyright: str
    # Navigation (populated by writer when building full vault)
    prev: str | None = None
    next: str | None = None
```

---

## 5. Canon Support

The `bgmd.canon` module owns all canonical data. No hardcoding in other modules.

```python
# books/catholic.csv — columns: slug, display_name, chapters, bg_name, testament
# bg_name is the exact string BibleGateway uses in URLs

# Example rows:
# tobit,Tobit,14,Tobit,OT-Deuterocanon
# judith,Judith,16,Judith,OT-Deuterocanon
# 1maccabees,1 Maccabees,16,1+Maccabees,OT-Deuterocanon
```

Supported canons in v1:
- `catholic` — 73 books (46 OT including Deuterocanonicals, 27 NT)
- `protestant` — 66 books
- `orthodox` — 76–81 books (configurable, lower priority)

Default canon: `catholic` (matches project history and primary use case).

---

## 6. CLI Interface

### 6.1 Primary Commands

```bash
# Single verse
bgmd fetch "John 3:16"
bgmd fetch "Jn 3:16" --translation RSV2CE

# Verse range
bgmd fetch "Romans 8:28-39"

# Chapter
bgmd fetch "Genesis 1"

# Full book
bgmd fetch "Tobit"

# Full Bible vault
bgmd fetch --all --translation NABRE --output ./bible-vault/

# Multiple references (batch)
bgmd fetch "Gen 1" "Ps 23" "Jn 1:1-18" --output ./passages/
```

### 6.2 Flags

| Flag | Default | Description |
|---|---|---|
| `--translation` / `-t` | `NABRE` | BibleGateway translation code |
| `--canon` | `catholic` | Canon set for full-Bible operations |
| `--output` / `-o` | `./output/` | Output directory |
| `--format` | `obsidian` | Output style (see §7) |
| `--footnotes` | `true` | Include footnotes |
| `--crossrefs` | `true` | Include cross-references |
| `--headings` | `true` | Include section headings |
| `--cache` | `true` | Use disk cache (`~/.cache/bgmd/`) |
| `--cache-dir` | `~/.cache/bgmd/` | Override cache location |
| `--concurrency` | `3` | Parallel fetch workers |
| `--dry-run` | `false` | Resolve + report targets, don't fetch |
| `--flat` | `false` | Single file output (no directory tree) |

### 6.3 Config File

`~/.config/bgmd/config.toml`:
```toml
translation = "NABRE"
canon = "catholic"
format = "obsidian"
concurrency = 3
cache = true
```

CLI flags override config. Config overrides defaults.

---

## 7. Output Format

### 7.1 File Structure (vault mode)

```
bible-vault/
├── _index.md                   # Bible index with all books
├── Old Testament/
│   ├── Genesis/
│   │   ├── Genesis 1.md
│   │   ├── Genesis 2.md
│   │   └── ...
│   ├── Tobit/
│   │   └── Tobit 1.md
│   └── ...
└── New Testament/
    └── John/
        ├── John 1.md
        └── ...
```

### 7.2 Chapter File Structure

```markdown
---
book: John
chapter: 3
translation: NABRE
aliases:
  - Jn 3
  - John 3
  - John Chapter 3
prev: "[[John 2]]"
next: "[[John 4]]"
tags:
  - bible/new-testament/john
---

# John 3

## Nicodemus

###### 1
Now there was a Pharisee named Nicodemus, a ruler of the Jews.^[a]

###### 2
He came to Jesus at night and said to him, "Rabbi, we know that you are a teacher
who has come from God, for no one can do these signs that you are doing unless God
is with him."

## Born of Water and Spirit

###### 16
For God so loved the world that he gave his only Son, so that everyone who
believes in him might not perish but might have eternal life.^[b]

---

## Footnotes

**a.** *v.1* — Some manuscripts add "of the Jews."
**b.** *v.16* — Or "his only-begotten Son."

## Cross-References

**a.** *v.1* — [Num 11:16](Num 11), [Acts 5:34](Acts 5)
```

### 7.3 Format Modes

| Mode | Description |
|---|---|
| `obsidian` | H6 verse numbers, WikiLinks, YAML Properties, callout blocks for footnotes |
| `plain` | No WikiLinks, plain Markdown, footnotes as standard MD footnote syntax |
| `minimal` | Text only, verse numbers inline (e.g., `¹ In the beginning...`) |

### 7.4 Verse Number Rendering

`obsidian` mode: `###### 16` (H6, enables CSS-based toggling in Obsidian)  
`plain` mode: `**16**` (bold inline)  
`minimal` mode: superscript Unicode or bracketed `[16]`

---

## 8. Parser Design

### 8.1 Approach

No regex-based HTML scraping. Use BeautifulSoup + lxml for DOM traversal. Target stable semantic CSS classes, not structural position.

```python
from bs4 import BeautifulSoup

def parse_passage(html: str, book: str, chapter: int, translation: str) -> PassageDoc:
    soup = BeautifulSoup(html, "lxml")
    passage_div = soup.select_one("div.passage-content")  # primary container
    ...
```

### 8.2 Extraction Targets

Selectors verified against `bg2md.rb` source and cross-referenced with multiple independent scrapers. **Do not trust these without a live page dump before writing the parser** — BibleGateway has changed its DOM before.

| Element | CSS Selector | Maps To | Notes |
|---|---|---|---|
| Content root | `div.passage-col` | Root | ⚠️ NOT `passage-content` — would return nothing |
| Passage title | `.bcv` | metadata | book/chapter/verse display string |
| Verse text | `span.text` | `Verse.text` | ✅ confirmed across sources |
| Verse numbers | `sup.versenum` | `Verse.number` | ✅ confirmed across sources |
| Chapter drop cap | `span.chapternum` | strip | redundant with file metadata |
| Section headings | `h3` | `SectionHeader` | primary; fallback to `h1,h2,h4,h5,h6` if absent |
| Footnote refs (inline) | `sup.footnote > a` | `Verse.footnote_refs` | ✅ confirmed across sources |
| Footnote container | `.footnotes` | — | parent list element |
| Footnote text | `span.footnote-text` | `Footnote.text` | ⚠️ NOT `li.footnote` — that's the list item, not the text |
| Cross-ref container | `.crossrefs` | — | parent list element |
| Cross-ref items | `.crossreference` | `CrossRef` | on the `li`; class name stable |
| Cross-ref links | `a.crossref-link` | `CrossRef.targets` | extract `href` for target reference |
| Copyright | `div.publisher-info` | `PassageDoc.copyright` | ⚠️ NOT `div.copyright-table` |

**Content bounds** (`?interface=print` DOM):  
Passage content starts at `h1.passage-display` and ends before `section.other-resources` or `section.sponsors`. Scope all selectors within these bounds to avoid picking up sidebar content.

```python
def parse_passage(html: str, ...) -> PassageDoc:
    soup = BeautifulSoup(html, "lxml")
    root = soup.select_one("div.passage-col")
    # Trim everything after .other-resources / .sponsors
    for el in root.select("section.other-resources, section.sponsors"):
        el.decompose()
    ...
```

### 8.3 Fallback Strategy

If a primary selector returns nothing, log a warning and attempt one fallback selector per element. If fallback also fails, record the failure in a structured error and continue (don't crash the batch). Full-Bible runs must tolerate partial failures.

---

## 9. Fetcher Design

### 9.1 HTTP

- Library: `curl_cffi` (libcurl-backed, browser TLS fingerprint impersonation)
- Base URL: `https://www.biblegateway.com/passage/?search={ref}&version={translation}&interface=print`
- `?interface=print` is load-bearing: it strips navigation chrome, ads, and sidebar content, producing a much smaller and more stable DOM. The passage content bounds (`h1.passage-display` → `section.other-resources`) are reliable specifically on this interface. Do not scrape the standard page — the DOM is materially different and the selectors in §8.2 will not hold.
- Impersonate: `chrome` (default) — matches JA3/JA4 fingerprint of current Chrome release

**Why `curl_cffi` over `httpx`:**  
Standard Python HTTP clients (requests, httpx, aiohttp) produce a distinct TLS fingerprint — cipher suite ordering, extension list, GREASE values — that differs from real browsers. BibleGateway doesn't actively fingerprint today, but any CDN-level bot protection (Cloudflare, Akamai) keys on this. `curl_cffi` wraps libcurl with BoringSSL and ships pre-built browser fingerprints, eliminating the detection vector at zero complexity cost.

```python
from curl_cffi.requests import AsyncSession

async def fetch_chapter(url: str) -> str:
    async with AsyncSession(impersonate="chrome") as session:
        resp = await session.get(url, timeout=30)
        resp.raise_for_status()
        return resp.text
```

### 9.2 Rate Limiting

- Default: 3 concurrent workers, 1 req/sec minimum interval per worker
- Configurable via `--concurrency`
- Respect `Retry-After` headers if present (BibleGateway occasionally throttles)
- Exponential backoff: 1s → 2s → 4s → 8s, max 3 retries

### 9.3 Disk Cache

- Location: `~/.cache/bgmd/{translation}/{book}/{chapter}.html`
- Cache key: `(translation, book, chapter)`
- No TTL by default (Scripture text doesn't change)
- `--no-cache` to bypass; `bgmd cache clear` to purge

---

## 10. Error Handling

| Error Type | Behavior |
|---|---|
| HTTP 429 (rate limit) | Backoff + retry |
| HTTP 404 | Log error, skip, continue batch |
| Parse failure (no passage found) | Log structured error, skip |
| Unknown book/translation | Fail fast with clear message |
| Network timeout | Retry up to 3x, then skip |

Batch runs produce an `errors.json` in the output directory listing all failures with book, chapter, and reason. Supports re-running failed fetches: `bgmd retry --errors ./bible-vault/errors.json`.

---

## 11. Translation Support

BibleGateway supports 50+ translations. `bgmd` doesn't enumerate them — it passes the translation code directly and fails gracefully if BibleGateway rejects it.

Common Catholic-use translations:
| Code | Translation |
|---|---|
| `NABRE` | New American Bible Revised Edition |
| `RSV2CE` | Revised Standard Version Catholic Edition |
| `DRA` | Douay-Rheims |
| `NRSVCE` | New Revised Standard Version Catholic Edition |
| `ESV` | English Standard Version |

---

## 12. Project Layout

```
bgmd/
├── pyproject.toml
├── README.md
├── debian/                     # Debian packaging
├── bgmd/
│   ├── __init__.py
│   ├── cli.py                  # Typer app
│   ├── resolver.py
│   ├── fetcher.py
│   ├── parser.py
│   ├── formatter.py
│   ├── writer.py
│   ├── models.py
│   ├── canon.py
│   └── books/
│       ├── catholic.csv
│       ├── protestant.csv
│       └── orthodox.csv
└── tests/
    ├── fixtures/               # Saved HTML snapshots for parser tests
    ├── test_resolver.py
    ├── test_parser.py
    └── test_formatter.py
```

---

## 13. Dependencies

```toml
[project]
requires-python = ">=3.11"

dependencies = [
    "typer[all]>=0.12",         # CLI
    "curl-cffi>=0.7",           # Async HTTP w/ browser TLS fingerprinting
    "beautifulsoup4>=4.12",     # HTML parsing
    "lxml>=5.0",                # Fast BS4 backend
    "rich>=13.0",               # Progress bars, console output
    "tomllib",                  # Config parsing (stdlib 3.11+)
]

[project.optional-dependencies]
dev = [
    "pytest",
    "pytest-asyncio",
    "respx",                    # Mock HTTP for curl_cffi (httpx-compatible interface)
    "ruff",
    "mypy",
]
```

---

## 14. Implementation Phases

### Phase 1 — Core (MVP)
- [ ] `models.py` — define all dataclasses
- [ ] `canon.py` + `books/catholic.csv` — Catholic canon data
- [ ] `fetcher.py` — single synchronous fetch (no async yet)
- [ ] `parser.py` — full parser with BeautifulSoup
- [ ] `formatter.py` — `obsidian` mode only
- [ ] `writer.py` — single file output
- [ ] `cli.py` — `fetch` command, single verse/chapter

### Phase 2 — Batch + Vault
- [ ] `resolver.py` — expand book/range refs to target lists
- [ ] Async fetcher with concurrency + rate limiting
- [ ] Disk cache
- [ ] Directory tree output (vault mode)
- [ ] `_index.md` generation
- [ ] Error reporting (`errors.json` + `retry` command)

### Phase 3 — Polish
- [ ] `plain` and `minimal` format modes
- [ ] Config file support
- [ ] `cache clear` subcommand
- [ ] `--dry-run`
- [ ] Protestant + Orthodox canon files
- [ ] Debian packaging (`debian/` directory)
- [ ] PyPI release

---

## 15. Key Tradeoffs

| Decision | Chosen | Alternative | Reason |
|---|---|---|---|
| HTML parsing | BeautifulSoup | Regex (legacy) | DOM-based is more resilient to BG HTML changes |
| HTTP client | curl_cffi | httpx / requests | Browser TLS fingerprinting eliminates primary bot-detection vector |
| CLI framework | Typer | Click, argparse | Pydantic-backed, auto-generates help, type safety |
| Output default | Obsidian-optimized | Generic MD | Matches primary use case; generic modes added later |
| Canon default | Catholic | Protestant | Project history + stated use case |
| Verse numbering | H6 headers | Inline bold | Enables Obsidian CSS snippet toggling |
| Caching | Filesystem | SQLite | Simpler, inspectable, no extra dep |
| Language | Python | Go | DOM parsing ecosystem, iteration speed |

---

## 16. Open Questions

1. **Copyright compliance** — NABRE and RSV2CE have reproduction limits. Full-Bible vault generation may exceed fair use. Need to assess whether caching raw HTML locally is a concern. Likely fine for personal use; document the limitation.
2. **BibleGateway ToS** — Scraping is technically against their ToS. Tool is for personal/scholarly use. Rate limiting and caching minimize server load. Consider adding a prominent disclaimer.
3. **Passage API** — No undocumented BibleGateway JSON API exists. Every third-party library in the ecosystem is an HTML scraper. `curl_cffi` + `interface=print` is the correct approach. Closed.

4. **Interlinear / original language** — Out of scope for v1 but the data model should not preclude adding Greek/Hebrew interlinear support later.
