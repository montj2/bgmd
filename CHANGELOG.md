# Changelog

All notable changes to this project will be documented in this file.

## [0.1.9] - 2026-03-09
### Fixed
- Fixed Daniel 3 numbering for Catholic lectionary. References from the USCCB (using NABRE numbering) are now correctly mapped to the internal numbering of other translations like RSVCE.
- Re-engineered the parser to handle multiple verses within a single HTML span, common in many Bible Gateway translations.
- Implemented verse priority to correctly choose Greek additions over Hebrew text when both exist in the same chapter (e.g. Daniel 3).

## [0.1.8] - 2026-03-09
### Added
- Support for disjoint verse ranges (references with commas, e.g., "Daniel 3:25, 34-43") in the lectionary and fetch commands.
- Implemented automatic full-chapter fallback when disjoint ranges are requested to ensure all verse spans are captured.

## [0.1.7] - 2026-03-09
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
