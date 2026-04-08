# convert_strava_tcx_to_garmin -- Interface Map

## Project Structure

```
convert_strava_tcx_to_garmin/
  tcx_converter.py           # Main module: all conversion logic + CLI
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
| `create_garmin_root()` | `tcx_converter.py` | Creates root XML element with Garmin namespaces |
| `convert_activity_to_garmin_format()` | `tcx_converter.py` | Converts Activity element (sets Sport="Other", formats timestamps) |
| `convert_lap_to_garmin_format()` | `tcx_converter.py` | Converts Lap element with extensions |
| `convert_track_to_garmin_format()` | `tcx_converter.py` | Converts Track element |
| `convert_trackpoint_to_garmin_format()` | `tcx_converter.py` | Converts Trackpoint: adds GPS, altitude, speed |
| `add_garmin_author_section()` | `tcx_converter.py` | Appends Garmin Author/Build metadata |
| `write_garmin_format_file()` | `tcx_converter.py` | Writes XML with exact Garmin formatting |
| `process_batch()` | `tcx_converter.py` | Batch-converts all TCX files in a folder |
| `main()` | `tcx_converter.py` | CLI entry point (argparse) |

## Configuration Constants

| Constant | Default | Purpose |
|---|---|---|
| `DEFAULT_LAT` | 30.2672 | Latitude for indoor activities (Austin, TX) |
| `DEFAULT_LNG` | -97.7431 | Longitude for indoor activities (Austin, TX) |
| `DEFAULT_ALTITUDE` | "192.60..." | Altitude in meters for trackpoints |
| `DEFAULT_AVG_SPEED` | "4.98..." | Average speed for lap extensions (m/s) |
