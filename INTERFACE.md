# convert_strava_tcx_to_garmin -- Interface Map

## Project Structure

```
convert_strava_tcx_to_garmin/
  tcx_core.py                # Conversion logic: TCX bytes in -> Garmin XML text out (no file I/O)
  tcx_converter.py           # CLI, file + batch handling; re-exports the tcx_core names
  test_tcx_converter.py      # Unit + regression tests with sample TCX fragments
  run_web.py                 # Starts the local web app (uvicorn, http://127.0.0.1:8153)
  requirements-web.txt       # Pinned deps for the web app and its tests (converter itself: stdlib only)
  web/
    __init__.py              # Package docstring listing the contents
    app.py                   # FastAPI: static front end, GET /api/info, /api/samples, POST /api/convert; STATIC_ENDPOINTS
    static/
      index.html, style.css  # Page shell + shared web-kit theme (style.css unchanged from the kit)
      style_app.css          # Project accent colours and page styles
      core.js                # Web-kit helpers + hash router (unchanged from the kit)
      main.js                # Registers pages, footer mode text, background animation
      static_api.js          # Answers api() on the static site from exported JSON
      home.js, convert.js, convert_view.js, about.js   # Pages (convert_view.js renders one file card)
      tcx_engine.js          # JS port of tcx_core.py (convertTcx), byte-identical output
      tcx_xml.js             # ElementTree semantics: parseXml, indent, tostring
      tcx_pyfmt.js           # Python semantics: str.strip, float(), float repr, splitext, fromisoformat -> UTC
      tcx_summary.js         # Preview: summarize() (distance, duration, laps, HR, power, route) and routeSvg()
      zip.js                 # Tiny stored-zip writer (crc32, makeZip, uniqueNames)
      tcx_engine.test.mjs    # Node test: JS vs Python fixtures (run by tests/test_web.py)
      icon.svg
  scripts/
    build_static.py          # Exports the static GitHub Pages site to site/
    screenshots.py           # Playwright smoke test + README screenshots (docs/img/)
    make_tcx_fixture.py      # Writes the Python reference outputs in tests/fixtures/
  tests/
    test_web.py              # API, static build, fixtures current, node tests
    test_js_port.py          # JS vs Python on 800 seeded mutated files; zip readable by zipfile
    fixtures/                # Synthetic samples (*.tcx, invented data), expected/ Python outputs, tcx_values.json
  .github/workflows/pages.yml  # Tests + publishes the static site on push to main
  docs/img/                  # README screenshots
  .gitignore                 # Ignores *_garmin.tcx output files, site/, caches
  README.md, ROADMAP.md, SESSION_LOG.md, INTERFACE.md
```

## How the pieces connect

- `tcx_converter.py` (CLI) -> `tcx_core.convert_tcx_bytes()`; `web/app.py` POST /api/convert -> the same function.
- The browser converts with `tcx_engine.js`, which mirrors `tcx_core.py` function for function; any change to the
  Python conversion must be mirrored there, then rerun `python scripts/make_tcx_fixture.py` and the tests.

## Key Functions

| Function | File | Purpose |
|---|---|---|
| `clean_tcx_for_garmin()` | `tcx_converter.py` | Main entry: converts a single TCX file to Garmin format |
| `convert_tcx_bytes()` | `tcx_core.py` | Converts TCX data (bytes/str) and returns the Garmin XML text |
| `garmin_xml_string()` | `tcx_core.py` | Serialises the converted tree in the exact Garmin layout |
| `local_name()`, `find_child()` | `tcx_core.py` | Namespace-free tag name; first child by local name |
| `format_garmin_time()` | `tcx_core.py` | ISO time -> `YYYY-MM-DDTHH:MM:SS.000Z` in UTC (unparseable text unchanged) |
| `create_garmin_root()` | `tcx_core.py` | Creates root XML element with Garmin namespaces |
| `convert_activity_to_garmin_format()` | `tcx_core.py` | Converts Activity element (sets Sport="Other", formats timestamps) |
| `convert_lap_to_garmin_format()` | `tcx_core.py` | Converts Lap element with extensions |
| `convert_track_to_garmin_format()` | `tcx_core.py` | Converts Track element |
| `convert_trackpoint_to_garmin_format()` | `tcx_core.py` | Converts Trackpoint: placeholder GPS/altitude for indoor activities, speed |
| `add_garmin_author_section()` | `tcx_core.py` | Appends Garmin Author/Build metadata |
| `write_garmin_format_file()` | `tcx_converter.py` | Writes a converted tree to a file (via `garmin_xml_string`) |
| `garmin_output_name()` | `tcx_converter.py` | `ride.tcx` -> `ride_garmin.tcx` |
| `print_changes()` | `tcx_converter.py` | Prints `GARMIN_CHANGES` (verbose mode) |
| `process_batch()` | `tcx_converter.py` | Batch-converts all TCX files in a folder |
| `main()` | `tcx_converter.py` | CLI entry point (argparse) |

## Configuration Constants (all in `tcx_core.py`)

| Constant | Default | Purpose |
|---|---|---|
| `DEFAULT_LAT` | 30.2672 | Latitude for indoor activities (Austin, TX) |
| `DEFAULT_LNG` | -97.7431 | Longitude for indoor activities (Austin, TX) |
| `DEFAULT_ALTITUDE` | "192.60..." | Altitude in meters for trackpoints |
| `DEFAULT_AVG_SPEED` | "4.98..." | Average speed for lap extensions (m/s) |
| `GARMIN_CHANGES` | list | Changes the conversion makes (CLI `-v`, web app) |
