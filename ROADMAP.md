# Strava TCX to Garmin Converter -- Roadmap

## Current State
A single-file Python script (`tcx_converter.py`) that converts Strava-exported TCX files for Garmin Connect compatibility. Handles namespace fixing, sport type changes, timestamp formatting, dummy GPS for indoor activities, and altitude data. Supports single file and batch processing with CLI arguments. Zero external dependencies (uses only built-in `xml.etree`, `argparse`, etc.). Well-documented README with clear workflow.

## Short-term Improvements
- [x] Add unit tests with sample TCX fragments (valid Strava input -> expected Garmin output)
- [x] Add validation that input files are valid TCX/XML before processing
- [ ] Handle edge cases: empty trackpoint lists, missing heart rate data, corrupted XML
- [ ] Add `--sport` flag to set activity type (Biking, Running, Other) instead of hardcoding "Other"
- [ ] Add `--dry-run` flag to preview changes without writing files
- [ ] Improve logging: use Python `logging` module instead of `print()` statements

## Feature Enhancements
- [ ] Add FIT file output support (more reliable for Garmin Connect import)
- [ ] Support GPX to TCX conversion in addition to TCX-to-TCX reformatting
- [ ] Add activity type auto-detection from TCX metadata
- [ ] Implement power-to-speed conversion with configurable FTP and rider weight
- [ ] Add summary statistics output (duration, distance, avg HR, avg power) after conversion
- [ ] Support reading from Strava API directly (OAuth + activity download)
- [ ] Add GUI mode using Tkinter for drag-and-drop file conversion

## Long-term Vision
- [ ] Build a cross-platform desktop app for non-technical users
- [ ] Add Garmin Connect API upload integration (convert + upload in one step)
- [ ] Support bidirectional conversion (Garmin -> Strava format)
- [ ] Create a web service version for browser-based conversion
- [ ] Package as a pip-installable CLI tool (`pip install strava2garmin`)

## Technical Debt
- [ ] Single-file architecture will become unwieldy if FIT/GPX support is added -- plan module split
- [x] Default GPS coordinates (Austin, TX) are hardcoded -- move to a config section
- [ ] Power-to-speed conversion formula accuracy should be validated against known cycling physics
- [x] No `.gitignore` for converted output files
- [ ] `argparse` setup could use subcommands (`convert`, `batch`, `validate`) for cleaner CLI
- [x] Bare except clauses replaced with specific exception types
