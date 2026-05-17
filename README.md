# TCX File Converter for Garmin Connect

A Python script that converts Strava-exported TCX files to be compatible with Garmin Connect import. Perfect for getting your Peloton workouts from Strava into Garmin Connect!

## 🎯 What Does This Solve?

Garmin Connect often rejects TCX files exported from Strava with the error "We don't support the file type you tried to import." This script fixes the formatting issues and makes your files compatible with Garmin Connect's strict requirements.

## ✨ Features

- **Single file conversion** - Convert one TCX file at a time
- **Batch processing** - Convert entire folders of TCX files automatically
- **Garmin-compatible format** - Matches exact Garmin Connect XML structure
- **Indoor activity support** - Adds dummy GPS coordinates for indoor workouts
- **Power data preservation** - Keeps all your important workout metrics
- **Progress tracking** - Shows conversion progress for batch operations
- **Error handling** - Continues processing even if individual files fail

## 📋 Requirements

- Python 3.6 or higher
- No additional packages required (uses built-in libraries only)

## 🚀 Installation

1. Download the `tcx_converter.py` script
2. Make it executable (optional):
   ```bash
   chmod +x tcx_converter.py
   ```

## 📖 Usage

### Single File Conversion

Convert a single TCX file:
```bash
python tcx_converter.py input_file.tcx
```

Specify output filename:
```bash
python tcx_converter.py input_file.tcx -o converted_file.tcx
```

### Batch Processing

Convert all TCX files in a folder:
```bash
python tcx_converter.py /path/to/folder/with/tcx/files
```

Put converted files in a separate output folder:
```bash
python tcx_converter.py /path/to/input/folder -o /path/to/output/folder
```

### Command Line Options

| Option | Description |
|--------|-------------|
| `input_path` | Input TCX file OR folder containing TCX files |
| `-o, --output` | Output file path OR output folder |
| `-v, --verbose` | Show detailed information about changes made |
| `--lat` | Default latitude for indoor activities (default: Austin, TX) |
| `--lng` | Default longitude for indoor activities (default: Austin, TX) |
| `--batch` | Force batch mode even when given a single file |

## 💡 Examples

### Example 1: Single File
```bash
python tcx_converter.py "30_min_Power_Zone_Ride.tcx"
```
**Output:**
```
Successfully converted '30_min_Power_Zone_Ride.tcx' to '30_min_Power_Zone_Ride_garmin.tcx'
```

### Example 2: Batch Processing with Verbose Output
```bash
python tcx_converter.py ~/Downloads/strava_exports/ -o ~/Desktop/garmin_ready/ -v
```
**Output:**
```
Batch mode: Processing all TCX files in folder '/Users/george/Downloads/strava_exports'
Found 5 TCX files to process...
Processing 1/5: workout1.tcx
  ✓ Successfully converted to workout1_garmin.tcx
Processing 2/5: workout2.tcx
  ✓ Successfully converted to workout2_garmin.tcx
...

==================================================
BATCH PROCESSING COMPLETE
==================================================
Total files: 5
Successful: 5
Failed: 0

✓ Successfully converted files:
  workout1.tcx → workout1_garmin.tcx
  workout2.tcx → workout2_garmin.tcx
  ...

Changes made to match Garmin Connect format exactly:
- Multi-line root element with exact namespace order
- Changed Sport to 'Other' (like working Garmin files)
- Added .000Z timestamp format
- Used ns3:TPX extensions format
- Added Garmin-style Author section with Connect Api
- Added dummy GPS coordinates for indoor activity
- Added AltitudeMeters to all trackpoints
- Converted power data to speed estimates
- Maintained all timing and distance data
- Used GPS coordinates: 30.2672, -97.7431 (Default: Austin, TX)
```

### Example 3: Custom Location
```bash
python tcx_converter.py workout.tcx --lat 40.7128 --lng -74.0060
```
This sets the dummy GPS coordinates to New York City instead of the default Austin, TX.

## 🔧 What the Conversion Does

The script transforms Strava TCX files to match Garmin Connect's exact requirements:

### Structural Changes
- **XML namespace declarations** - Adds proper Garmin namespace structure
- **Multi-line root element** - Formats the root element exactly like Garmin exports
- **Activity Sport type** - Changes from "Biking" to "Other" (required by Garmin)
- **Author section** - Adds Garmin-style metadata with "Connect Api" signature

### Data Enhancements
- **GPS coordinates** - Adds dummy latitude/longitude for indoor activities
- **Altitude data** - Adds required AltitudeMeters to all trackpoints
- **Timestamp format** - Converts to `.000Z` format (e.g., `2025-05-22T21:09:59.000Z`)
- **Speed data** - Converts power measurements to estimated speed values
- **Extensions format** - Uses proper `ns3:TPX` namespace format

### Preserved Data
- ✅ All timing information
- ✅ Distance measurements
- ✅ Heart rate data
- ✅ Power/cadence data (converted to speed estimates)
- ✅ Workout duration and calories
- ✅ All performance metrics

## 🔥 Perfect Workflow for Peloton Users

1. **Export from Strava** - Download your Peloton workouts as TCX files
2. **Batch convert** - Run this script on your download folder
3. **Import to Garmin** - Upload the converted files to Garmin Connect
4. **Enjoy** - All your Peloton data now appears in Garmin Connect!

```bash
# One command to convert all your Peloton exports:
python tcx_converter.py ~/Downloads/strava_exports/ -o ~/Desktop/garmin_ready/ -v
```

## ❗ Troubleshooting

### "No TCX files found"
- Make sure your files have `.tcx` extension (case-insensitive)
- Check that the folder path is correct

### "Invalid TCX file"
- The original TCX file may be corrupted
- Try re-exporting from Strava
- Use the verbose flag (`-v`) to see detailed error information

### Garmin Connect still rejects files
- Double-check that you're uploading the `_garmin.tcx` files, not the originals
- Try uploading one file at a time instead of bulk upload
- Clear your browser cache and try again
- Some very large files may need to be split into smaller segments

### Files are too large
- Garmin Connect has size limits for uploads
- Try using fewer trackpoints or shorter time periods
- Consider using the GOTOES tool to convert to FIT format instead

## 🔄 Alternative: Converting to FIT Format

If TCX files still don't work, you can convert them to FIT format using the GOTOES tool:

1. Go to: https://gotoes.org/strava/Combine_GPX_TCX_FIT_Files.php
2. Upload your converted TCX file
3. Select "FIT" as the export format
4. Download and upload the FIT file to Garmin Connect

FIT format has higher success rates with Garmin Connect.

## 📝 Technical Details

This script addresses the specific formatting differences between Strava-exported TCX files and the format that Garmin Connect expects. The key insight came from analyzing working Garmin TCX files and matching their exact structure, namespaces, and data organization.

### Why Indoor Activities Need GPS Data
Even though indoor cycling doesn't involve GPS, Garmin Connect requires position data for all activities. The script adds dummy coordinates (default: Austin, TX) as placeholders.

### Namespace Magic
The script uses the exact namespace declarations and prefixes that Garmin Connect expects, including the multi-line root element format that Garmin uses in their own exports.


## 📄 License

This script is provided as-is for personal use. Feel free to modify and distribute.

## 🙏 Credits

Developed to solve the common issue of importing Strava TCX exports into Garmin Connect.

---

**Happy converting! 🚴‍♂️💪**


---
*Built with AI assistance from [Claude (Anthropic)](https://claude.com/).*
