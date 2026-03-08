# Changelog

All notable changes to this project will be documented in this file.

## [0.1.6] - 2026-03-08
### Added
- Implemented automatic Psalm numbering mapping for Vulgate-style translations (DRA, VULGATE). This allows users to use modern Masoretic numbering (e.g. Psalm 23) and automatically receive the correct traditional content (e.g. DRA Psalm 22).
- Added `--no-psalm-map` flag to disable this behavior.

## [0.1.5] - 2026-03-08
### Fixed
- Fixed Markdown table formatting in `compare` and `lectionary` commands by bypassing terminal formatting and normalizing whitespace.

## [0.1.4] - 2026-03-08
### Added
- Added parallel translation comparison to the `lectionary` command.
- Documented comparison features in README and man page.

## [0.1.3] - 2026-03-08
### Added
- Implemented parallel translation comparison with `compare` command.
- Added support for comma-separated translations in `fetch` command.
- Added table and interleaved layouts for comparisons.

## [0.1.2] - 2026-03-08
### Fixed
- Fixed verse range extraction for translations where the first verse is tagged as a chapter number.
- Fixed Psalm mapping in lectionary fetching.

## [0.1.1] - 2026-03-08
### Fixed
- Fixed `uv`/`global` installation issues by transitioning to a `src` layout.
- Fixed `typer[all]` extra dependency warning.

## [0.1.0] - 2026-03-08
### Added
- Initial release of `bgmd`.
- Robust DOM-based parsing of Bible Gateway content.
- Support for daily lectionary readings.
- Persistent configuration system.
- Global caching and request randomization.
- Obsidian-optimized Markdown output.
- Comprehensive system man page.
