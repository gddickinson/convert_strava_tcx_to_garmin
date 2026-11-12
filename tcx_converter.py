#!/usr/bin/env python3
"""
TCX File Converter for Garmin Connect Compatibility
Converts Strava-exported TCX files to match exact Garmin Connect format
Supports both single file and batch processing of entire folders

The conversion itself lives in tcx_core.py; this module adds file handling, batch mode and the CLI,
and re-exports the core names so `from tcx_converter import ...` keeps working.
"""

import argparse
import os

from tcx_core import (  # noqa: F401  (re-exported)
    DEFAULT_ALTITUDE,
    DEFAULT_LAT,
    DEFAULT_LNG,
    GARMIN_CHANGES,
    LX_FIELDS,
    add_garmin_author_section,
    convert_activity_to_garmin_format,
    convert_lap_extensions,
    convert_lap_to_garmin_format,
    convert_tcx_bytes,
    convert_track_to_garmin_format,
    convert_trackpoint_to_garmin_format,
    copy_element_recursive,
    create_garmin_root,
    garmin_xml_string,
    lap_avg_speed,
)


GARMIN_SUFFIX = '_garmin.tcx'


def garmin_output_name(input_file):
    """Default output name: 'ride.tcx' -> 'ride_garmin.tcx' (same folder)"""
    return f"{os.path.splitext(input_file)[0]}{GARMIN_SUFFIX}"


def clean_tcx_for_garmin(input_file, output_file=None, default_lat=DEFAULT_LAT, default_lng=DEFAULT_LNG):
    """
    Convert a TCX file to be compatible with Garmin Connect

    Args:
        input_file (str): Path to input TCX file
        output_file (str): Path to output TCX file (optional)
        default_lat: Default latitude for indoor activities
        default_lng: Default longitude for indoor activities

    Returns:
        str: Path to the output file
    """
    with open(input_file, 'rb') as f:
        text = convert_tcx_bytes(f.read(), default_lat, default_lng)

    # Generate output filename if not provided
    if output_file is None:
        output_file = garmin_output_name(input_file)

    # Never overwrite the original
    if os.path.exists(output_file) and os.path.samefile(input_file, output_file):
        raise ValueError(f"Output file '{output_file}' is the input file; choose another name")

    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(text)

    return output_file


def write_garmin_format_file(root, output_file):
    """Write file in exact Garmin format with proper indentation"""
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write(garmin_xml_string(root))


def print_changes(lat, lng):
    """Print the list of changes the conversion makes (verbose mode)"""
    print("\nChanges made to match Garmin Connect format exactly:")
    for change in GARMIN_CHANGES:
        print(f"- {change}")
    print(f"- Used GPS coordinates: {lat}, {lng}")
    if lat == DEFAULT_LAT and lng == DEFAULT_LNG:
        print("  (Default: Austin, TX)")


def process_batch(input_folder, output_folder=None, default_lat=DEFAULT_LAT, default_lng=DEFAULT_LNG):
    """
    Process all TCX files in a folder

    Args:
        input_folder (str): Path to folder containing TCX files
        output_folder (str): Path to output folder (optional)
        default_lat: Default latitude for indoor activities
        default_lng: Default longitude for indoor activities

    Returns:
        dict: Processing results
    """

    if not os.path.isdir(input_folder):
        raise ValueError(f"Input folder '{input_folder}' does not exist or is not a directory")

    # Find all TCX files, skipping the outputs of an earlier run (*_garmin.tcx)
    tcx_files, skipped = [], []
    for filename in sorted(os.listdir(input_folder)):
        if filename.lower().endswith(GARMIN_SUFFIX):
            skipped.append(filename)
        elif filename.lower().endswith('.tcx'):
            tcx_files.append(os.path.join(input_folder, filename))

    if not tcx_files:
        note = f" (skipped {len(skipped)} already converted *_garmin.tcx files)" if skipped else ""
        raise ValueError(f"No TCX files found in folder '{input_folder}'{note}")

    # Create output folder if specified
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    results = {
        'successful': [],
        'failed': [],
        'skipped': skipped,
        'total': len(tcx_files)
    }

    print(f"Found {len(tcx_files)} TCX files to process...")
    if skipped:
        print(f"Skipping {len(skipped)} already converted *_garmin.tcx files")

    for i, input_file in enumerate(tcx_files, 1):
        filename = os.path.basename(input_file)
        print(f"Processing {i}/{len(tcx_files)}: {filename}")

        try:
            # Generate output filename
            if output_folder:
                output_file = os.path.join(output_folder, garmin_output_name(filename))
            else:
                # Place in same folder as input
                output_file = garmin_output_name(input_file)

            # Process the file
            clean_tcx_for_garmin(input_file, output_file, default_lat, default_lng)
            results['successful'].append({
                'input': filename,
                'output': os.path.basename(output_file)
            })
            print(f"  ✓ Successfully converted to {os.path.basename(output_file)}")

        except Exception as e:
            results['failed'].append({
                'input': filename,
                'error': str(e)
            })
            print(f"  ✗ Failed: {e}")

    return results

def main():
    """Command line interface"""
    parser = argparse.ArgumentParser(description='Convert TCX files to exact Garmin Connect format')
    parser.add_argument('input_path', help='Input TCX file path OR folder containing TCX files')
    parser.add_argument('-o', '--output', help='Output TCX file path OR output folder (for batch processing)')
    parser.add_argument('-v', '--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--lat', type=float, default=DEFAULT_LAT,
                       help='Default latitude for indoor activities (default: Austin, TX)')
    parser.add_argument('--lng', type=float, default=DEFAULT_LNG,
                       help='Default longitude for indoor activities (default: Austin, TX)')
    parser.add_argument('--batch', action='store_true',
                       help='Force batch mode (process all .tcx files in folder)')

    args = parser.parse_args()

    if not os.path.exists(args.input_path):
        print(f"Error: Input path '{args.input_path}' not found")
        return 1

    # Determine if we're processing a single file or batch
    is_batch = args.batch or os.path.isdir(args.input_path)

    try:
        if is_batch:
            # Batch processing
            if os.path.isfile(args.input_path):
                # User specified --batch but gave a file, process the containing folder
                input_folder = os.path.dirname(args.input_path)
                print(f"Batch mode: Processing all TCX files in folder '{input_folder}'")
            else:
                input_folder = args.input_path
                print(f"Batch mode: Processing all TCX files in folder '{input_folder}'")

            results = process_batch(input_folder, args.output, args.lat, args.lng)

            # Print summary
            print(f"\n{'='*50}")
            print(f"BATCH PROCESSING COMPLETE")
            print(f"{'='*50}")
            print(f"Total files: {results['total']}")
            print(f"Successful: {len(results['successful'])}")
            print(f"Failed: {len(results['failed'])}")
            if results['skipped']:
                print(f"Skipped (already converted): {len(results['skipped'])}")

            if results['successful']:
                print(f"\n✓ Successfully converted files:")
                for item in results['successful']:
                    print(f"  {item['input']} → {item['output']}")

            if results['failed']:
                print(f"\n✗ Failed files:")
                for item in results['failed']:
                    print(f"  {item['input']}: {item['error']}")

            if args.verbose and results['successful']:
                print_changes(args.lat, args.lng)

            return 0 if not results['failed'] else 1

        else:
            # Single file processing
            output_file = clean_tcx_for_garmin(args.input_path, args.output, args.lat, args.lng)
            print(f"Successfully converted '{args.input_path}' to '{output_file}'")

            if args.verbose:
                print_changes(args.lat, args.lng)

            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
