# convert_strava_tcx_to_garmin -- Interface Map

## Project Structure

```
convert_strava_tcx_to_garmin/
  tcx_core.py                # Conversion logic: TCX bytes in -> Garmin XML text out (no file I/O)
  tcx_converter.py           # CLI, file + batch handling; re-exports the tcx_core names
  test_tcx_converter.py      # Unit tests with sample TCX fragments
  .gitignore                 # Ignores *_garmin.tcx output files
  README.md
  ROADMAP.md
  INTERFACE.md               # This file
```

## Key Functions

| Function | File | Purpose |
|---|---|---|
| `clean_tcx_for_garmin()` | `tcx_converter.py` | Main entry: converts a single TCX file to Garmin format |
| `convert_tcx_bytes()` | `tcx_core.py` | Converts TCX data (bytes/str) and returns the Garmin XML text |
| `garmin_xml_string()` | `tcx_core.py` | Serialises the converted tree in the exact Garmin layout |
| `format_garmin_time()` | `tcx_core.py` | ISO time -> `YYYY-MM-DDTHH:MM:SS.000Z` in UTC (unparseable text unchanged) |
| `create_garmin_root()` | `tcx_core.py` | Creates root XML element with Garmin namespaces |
| `convert_activity_to_garmin_format()` | `tcx_core.py` | Converts Activity element (sets Sport="Other", formats timestamps) |
| `convert_lap_to_garmin_format()` | `tcx_core.py` | Converts Lap element with extensions |
| `convert_track_to_garmin_format()` | `tcx_core.py` | Converts Track element |
| `convert_trackpoint_to_garmin_format()` | `tcx_core.py` | Converts Trackpoint: adds GPS, altitude, speed |
| `add_garmin_author_section()` | `tcx_core.py` | Appends Garmin Author/Build metadata |
| `write_garmin_format_file()` | `tcx_converter.py` | Writes a converted tree to a file (via `garmin_xml_string`) |
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
