"""
Conversion core for the Strava TCX -> Garmin Connect converter (no file or CLI handling).

Contents:
    DEFAULT_* constants, GARMIN_CHANGES   - configuration and the list of changes the conversion makes
    convert_tcx_bytes(data, lat, lng)     - TCX bytes in, Garmin-format XML text out (used by the CLI and web app)
    garmin_xml_string(root)               - serialise the converted tree in the exact Garmin layout
    create_garmin_root, convert_*_to_garmin_format, add_garmin_author_section, copy_element_recursive
"""

import xml.etree.ElementTree as ET
from datetime import datetime

# Default GPS coordinates for indoor activities (Austin, TX)
DEFAULT_LAT = 30.2672
DEFAULT_LNG = -97.7431
# Default altitude in meters for trackpoints without altitude data
DEFAULT_ALTITUDE = "192.60000610351562"
# Default average speed for lap extensions (m/s)
DEFAULT_AVG_SPEED = "4.9846988191804575"

# What the conversion changes (printed by the CLI with -v, shown by the web app)
GARMIN_CHANGES = [
    "Multi-line root element with exact namespace order",
    "Changed Sport to 'Other' (like working Garmin files)",
    "Added .000Z timestamp format",
    "Used ns3:TPX extensions format",
    "Added Garmin-style Author section with Connect Api",
    "Added dummy GPS coordinates for indoor activity",
    "Added AltitudeMeters to all trackpoints",
    "Converted power data to speed estimates",
    "Added ns3:LX lap extensions with average speed",
    "Maintained all timing and distance data",
]


def convert_tcx_bytes(data, default_lat=DEFAULT_LAT, default_lng=DEFAULT_LNG):
    """
    Convert the contents of a TCX file (bytes or str) and return the Garmin-format XML text

    Raises:
        ValueError: if the data is not well-formed XML
    """
    try:
        root = ET.fromstring(data)
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

    return garmin_xml_string(new_root)



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
            except (ValueError, AttributeError):
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
        except (ValueError, AttributeError):
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
            avg_speed.text = DEFAULT_AVG_SPEED
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
            except (ValueError, AttributeError):
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
    altitude_elem.text = DEFAULT_ALTITUDE

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
                            except (ValueError, TypeError):
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

def garmin_xml_string(root):
    """Serialise the converted tree in exact Garmin format with proper indentation"""

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

    return '\n'.join(lines)
