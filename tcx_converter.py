#!/usr/bin/env python3
"""
TCX File Converter for Garmin Connect Compatibility
Converts Strava-exported TCX files to match exact Garmin Connect format
Supports both single file and batch processing of entire folders
"""

import xml.etree.ElementTree as ET
from datetime import datetime
import argparse
import os
import re

def clean_tcx_for_garmin(input_file, output_file=None, default_lat=30.2672, default_lng=-97.7431):
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

    # Parse the input file
    try:
        tree = ET.parse(input_file)
        root = tree.getroot()
    except ET.ParseError as e:
        raise ValueError(f"Invalid TCX file: {e}")

    # Create completely new structure matching working Garmin format
    new_root = create_garmin_root()
    activities_elem = ET.SubElement(new_root, 'Activities')

    # Find original activities
    original_activities = None
    for elem in root.iter():
        if elem.tag.endswith('Activities') or elem.tag == 'Activities':
            original_activities = elem
            break

    if original_activities is not None:
        for activity in original_activities.findall('*'):
            new_activity = convert_activity_to_garmin_format(activity, default_lat, default_lng)
            activities_elem.append(new_activity)

    # Add Garmin-style Author section
    add_garmin_author_section(new_root)

    # Generate output filename if not provided
    if output_file is None:
        base_name = os.path.splitext(input_file)[0]
        output_file = f"{base_name}_garmin.tcx"

    # Write with exact Garmin formatting
    write_garmin_format_file(new_root, output_file)

    return output_file

def create_garmin_root():
    """Create root element with exact Garmin namespace format"""
    root = ET.Element('TrainingCenterDatabase')

    # Add namespaces in exact order as working Garmin file
    root.set('{http://www.w3.org/2001/XMLSchema-instance}schemaLocation',
             'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 '
             'http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd')
    root.set('xmlns:ns5', 'http://www.garmin.com/xmlschemas/ActivityGoals/v1')
    root.set('xmlns:ns3', 'http://www.garmin.com/xmlschemas/ActivityExtension/v2')
    root.set('xmlns:ns2', 'http://www.garmin.com/xmlschemas/UserProfile/v2')
    root.set('xmlns', 'http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2')
    root.set('xmlns:xsi', 'http://www.w3.org/2001/XMLSchema-instance')
    root.set('xmlns:ns4', 'http://www.garmin.com/xmlschemas/ProfileExtension/v1')

    return root

def convert_activity_to_garmin_format(activity, default_lat, default_lng):
    """Convert activity to match Garmin format exactly"""
    new_activity = ET.Element('Activity')

    # Force Sport to "Other" like working Garmin files
    new_activity.set('Sport', 'Other')

    # Process child elements
    for child in activity:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'Id':
            new_id = ET.SubElement(new_activity, 'Id')
            # Add .000Z format like Garmin
            try:
                dt = datetime.fromisoformat(child.text.replace('Z', '+00:00'))
                new_id.text = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            except:
                new_id.text = child.text

        elif tag == 'Creator':
            # Skip Creator - Garmin files don't have this
            pass

        elif tag == 'Lap':
            new_lap = convert_lap_to_garmin_format(child, default_lat, default_lng)
            new_activity.append(new_lap)

        elif tag == 'Extensions':
            # Skip activity-level extensions
            pass
        else:
            # Copy other elements
            new_activity.append(copy_element_recursive(child))

    return new_activity

def convert_lap_to_garmin_format(lap, default_lat, default_lng):
    """Convert lap to Garmin format"""
    new_lap = ET.Element('Lap')

    # Copy StartTime with .000Z format
    start_time = lap.get('StartTime')
    if start_time:
        try:
            dt = datetime.fromisoformat(start_time.replace('Z', '+00:00'))
            new_lap.set('StartTime', dt.strftime('%Y-%m-%dT%H:%M:%S.000Z'))
        except:
            new_lap.set('StartTime', start_time)

    # Copy lap-level elements
    for child in lap:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'Track':
            new_track = convert_track_to_garmin_format(child, default_lat, default_lng)
            new_lap.append(new_track)
        elif tag == 'Extensions':
            # Create Garmin-style lap extensions with average speed
            new_ext = ET.SubElement(new_lap, 'Extensions')
            lx_elem = ET.SubElement(new_ext, 'ns3:LX')
            avg_speed = ET.SubElement(lx_elem, 'ns3:AvgSpeed')
            avg_speed.text = "4.9846988191804575"  # Default value
        else:
            # Copy other lap elements
            new_lap.append(copy_element_recursive(child))

    return new_lap

def convert_track_to_garmin_format(track, default_lat, default_lng):
    """Convert track to Garmin format"""
    new_track = ET.Element('Track')

    for trackpoint in track:
        if trackpoint.tag.split('}')[-1] == 'Trackpoint':
            new_trackpoint = convert_trackpoint_to_garmin_format(trackpoint, default_lat, default_lng)
            new_track.append(new_trackpoint)

    return new_track

def convert_trackpoint_to_garmin_format(trackpoint, default_lat, default_lng):
    """Convert trackpoint to exact Garmin format"""
    new_trackpoint = ET.Element('Trackpoint')

    # Process in specific order: Time, Position, Altitude, Distance, Extensions

    # 1. Time with .000Z format
    for child in trackpoint:
        if child.tag.split('}')[-1] == 'Time':
            new_time = ET.SubElement(new_trackpoint, 'Time')
            try:
                dt = datetime.fromisoformat(child.text.replace('Z', '+00:00'))
                new_time.text = dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
            except:
                new_time.text = child.text
            break

    # 2. Position (always add)
    position_elem = ET.SubElement(new_trackpoint, 'Position')
    lat_elem = ET.SubElement(position_elem, 'LatitudeDegrees')
    lat_elem.text = str(default_lat)
    lng_elem = ET.SubElement(position_elem, 'LongitudeDegrees')
    lng_elem.text = str(default_lng)

    # 3. Altitude (always add)
    altitude_elem = ET.SubElement(new_trackpoint, 'AltitudeMeters')
    altitude_elem.text = "192.60000610351562"

    # 4. Distance (if present in original)
    for child in trackpoint:
        if child.tag.split('}')[-1] == 'DistanceMeters':
            new_distance = ET.SubElement(new_trackpoint, 'DistanceMeters')
            new_distance.text = child.text
            break

    # 5. Extensions in Garmin format
    new_ext = ET.SubElement(new_trackpoint, 'Extensions')
    tpx_elem = ET.SubElement(new_ext, 'ns3:TPX')

    # Add speed if we have power/cadence data (convert power to speed estimate)
    for child in trackpoint:
        if child.tag.split('}')[-1] == 'Extensions':
            for ext_child in child:
                if 'TPX' in ext_child.tag:
                    for data in ext_child:
                        if 'Watts' in data.tag and data.text:
                            # Rough conversion: watts to speed (very approximate)
                            try:
                                watts = float(data.text)
                                speed = max(0.1, watts / 50.0)  # Rough conversion
                                speed_elem = ET.SubElement(tpx_elem, 'ns3:Speed')
                                speed_elem.text = str(speed)
                            except:
                                pass
                            break
            break

    # If no speed was added, add a minimal speed
    if not tpx_elem.find('ns3:Speed'):
        if len(tpx_elem) == 0:
            # Empty TPX element like in working file
            pass
        else:
            speed_elem = ET.SubElement(tpx_elem, 'ns3:Speed')
            speed_elem.text = "0.1"

    return new_trackpoint

def add_garmin_author_section(root):
    """Add Garmin-style Author section"""
    author_elem = ET.SubElement(root, 'Author')
    author_elem.set('{http://www.w3.org/2001/XMLSchema-instance}type', 'Application_t')

    name_elem = ET.SubElement(author_elem, 'Name')
    name_elem.text = 'Connect Api'

    build_elem = ET.SubElement(author_elem, 'Build')
    version_elem = ET.SubElement(build_elem, 'Version')

    version_major = ET.SubElement(version_elem, 'VersionMajor')
    version_major.text = '25'
    version_minor = ET.SubElement(version_elem, 'VersionMinor')
    version_minor.text = '8'
    build_major = ET.SubElement(version_elem, 'BuildMajor')
    build_major.text = '0'
    build_minor = ET.SubElement(version_elem, 'BuildMinor')
    build_minor.text = '0'

    lang_elem = ET.SubElement(author_elem, 'LangID')
    lang_elem.text = 'en'

    part_elem = ET.SubElement(author_elem, 'PartNumber')
    part_elem.text = '006-D2449-00'

def copy_element_recursive(element):
    """Recursively copy an XML element"""
    tag = element.tag.split('}')[-1] if '}' in element.tag else element.tag
    new_element = ET.Element(tag)

    for key, value in element.attrib.items():
        new_element.set(key, value)

    if element.text:
        new_element.text = element.text

    if element.tail:
        new_element.tail = element.tail

    for child in element:
        new_element.append(copy_element_recursive(child))

    return new_element

def write_garmin_format_file(root, output_file):
    """Write file in exact Garmin format with proper indentation"""

    # Create the XML string manually to match Garmin format exactly
    lines = ['<?xml version="1.0" encoding="UTF-8"?>']

    # Multi-line root element like Garmin
    lines.append('<TrainingCenterDatabase')
    lines.append('  xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"')
    lines.append('  xmlns:ns5="http://www.garmin.com/xmlschemas/ActivityGoals/v1"')
    lines.append('  xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2"')
    lines.append('  xmlns:ns2="http://www.garmin.com/xmlschemas/UserProfile/v2"')
    lines.append('  xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"')
    lines.append('  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns4="http://www.garmin.com/xmlschemas/ProfileExtension/v1">')

    # Add the rest of the content
    ET.indent(root, space="  ", level=1)
    for child in root:
        child_str = ET.tostring(child, encoding='unicode')
        # Indent properly
        indented_lines = ['  ' + line if line.strip() else line for line in child_str.split('\n')]
        lines.extend(indented_lines[:-1])  # Skip last empty line

    lines.append('</TrainingCenterDatabase>')

    # Write to file
    with open(output_file, 'w', encoding='utf-8') as f:
        f.write('\n'.join(lines))

def process_batch(input_folder, output_folder=None, default_lat=30.2672, default_lng=-97.7431):
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

    # Find all TCX files
    tcx_files = []
    for filename in os.listdir(input_folder):
        if filename.lower().endswith('.tcx'):
            tcx_files.append(os.path.join(input_folder, filename))

    if not tcx_files:
        raise ValueError(f"No TCX files found in folder '{input_folder}'")

    # Create output folder if specified
    if output_folder and not os.path.exists(output_folder):
        os.makedirs(output_folder)

    results = {
        'successful': [],
        'failed': [],
        'total': len(tcx_files)
    }

    print(f"Found {len(tcx_files)} TCX files to process...")

    for i, input_file in enumerate(tcx_files, 1):
        filename = os.path.basename(input_file)
        print(f"Processing {i}/{len(tcx_files)}: {filename}")

        try:
            # Generate output filename
            if output_folder:
                base_name = os.path.splitext(filename)[0]
                output_file = os.path.join(output_folder, f"{base_name}_garmin.tcx")
            else:
                # Place in same folder as input
                base_name = os.path.splitext(input_file)[0]
                output_file = f"{base_name}_garmin.tcx"

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
    parser.add_argument('--lat', type=float, default=30.2672,
                       help='Default latitude for indoor activities (default: Austin, TX)')
    parser.add_argument('--lng', type=float, default=-97.7431,
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

            if results['successful']:
                print(f"\n✓ Successfully converted files:")
                for item in results['successful']:
                    print(f"  {item['input']} → {item['output']}")

            if results['failed']:
                print(f"\n✗ Failed files:")
                for item in results['failed']:
                    print(f"  {item['input']}: {item['error']}")

            if args.verbose and results['successful']:
                print(f"\nChanges made to match Garmin Connect format exactly:")
                print(f"- Multi-line root element with exact namespace order")
                print(f"- Changed Sport to 'Other' (like working Garmin files)")
                print(f"- Added .000Z timestamp format")
                print(f"- Used ns3:TPX extensions format")
                print(f"- Added Garmin-style Author section with Connect Api")
                print(f"- Added dummy GPS coordinates for indoor activity")
                print(f"- Added AltitudeMeters to all trackpoints")
                print(f"- Converted power data to speed estimates")
                print(f"- Added ns3:LX lap extensions with average speed")
                print(f"- Maintained all timing and distance data")
                print(f"- Used GPS coordinates: {args.lat}, {args.lng}")
                if args.lat == 30.2672 and args.lng == -97.7431:
                    print(f"  (Default: Austin, TX)")

            return 0 if not results['failed'] else 1

        else:
            # Single file processing
            output_file = clean_tcx_for_garmin(args.input_path, args.output, args.lat, args.lng)
            print(f"Successfully converted '{args.input_path}' to '{output_file}'")

            if args.verbose:
                print("\nChanges made to match Garmin Connect format exactly:")
                print("- Multi-line root element with exact namespace order")
                print("- Changed Sport to 'Other' (like working Garmin files)")
                print("- Added .000Z timestamp format")
                print("- Used ns3:TPX extensions format")
                print("- Added Garmin-style Author section with Connect Api")
                print("- Added dummy GPS coordinates for indoor activity")
                print("- Added AltitudeMeters to all trackpoints")
                print("- Converted power data to speed estimates")
                print("- Added ns3:LX lap extensions with average speed")
                print("- Maintained all timing and distance data")
                print(f"- Used GPS coordinates: {args.lat}, {args.lng}")
                if args.lat == 30.2672 and args.lng == -97.7431:
                    print("  (Default: Austin, TX)")

            return 0

    except Exception as e:
        print(f"Error: {e}")
        return 1


if __name__ == '__main__':
    exit(main())
