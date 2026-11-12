"""
Conversion core for the Strava TCX -> Garmin Connect converter (no file or CLI handling).

Contents:
    DEFAULT_* constants, GARMIN_CHANGES   - configuration and the list of changes the conversion makes
    convert_tcx_bytes(data, lat, lng)     - TCX bytes in, Garmin-format XML text out (used by the CLI and web app)
    garmin_xml_string(root)               - serialise the converted tree in the exact Garmin layout
    create_garmin_root, convert_*_to_garmin_format, add_garmin_author_section, copy_element_recursive
"""

import math
import xml.etree.ElementTree as ET
from datetime import datetime, timezone

# Default GPS coordinates for indoor activities (Austin, TX)
DEFAULT_LAT = 30.2672
DEFAULT_LNG = -97.7431
# Default altitude in meters for trackpoints without altitude data
DEFAULT_ALTITUDE = "192.60000610351562"
# Lap extension (ns3:LX) values kept from the input, in TCX ActivityExtension schema order
LX_FIELDS = ('AvgSpeed', 'MaxBikeCadence', 'AvgRunCadence', 'MaxRunCadence', 'Steps', 'AvgWatts', 'MaxWatts')

# What the conversion changes (printed by the CLI with -v, shown by the web app)
GARMIN_CHANGES = [
    "Multi-line root element with exact namespace order",
    "Changed Sport to 'Other' (like working Garmin files)",
    "Added .000Z timestamp format",
    "Used ns3:TPX extensions format",
    "Added Garmin-style Author section with Connect Api",
    "Added dummy GPS coordinates for indoor activity (recorded GPS is kept)",
    "Added AltitudeMeters to trackpoints of activities without altitude data",
    "Estimated speed from power where no speed was recorded",
    "Kept heart rate, cadence and power data",
    "Kept ns3:LX lap extensions (average speed from distance/time if not recorded)",
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



def local_name(tag):
    """Tag without its '{namespace}' part"""
    return tag.split('}')[-1]

def find_child(element, name):
    """First direct child whose tag (ignoring the namespace) is name, or None"""
    for child in element:
        if local_name(child.tag) == name:
            return child
    return None

def format_garmin_time(text):
    """
    Format an ISO 8601 time as Garmin's 'YYYY-MM-DDTHH:MM:SS.000Z' (UTC, fraction dropped)

    Times with a UTC offset are converted to UTC first; times without one are taken as UTC.
    Text that is not an ISO time (or None) is returned unchanged.
    """
    try:
        dt = datetime.fromisoformat(text.replace('Z', '+00:00'))
        if dt.tzinfo is not None:
            dt = dt.astimezone(timezone.utc)
        return dt.strftime('%Y-%m-%dT%H:%M:%S.000Z')
    except (ValueError, AttributeError, OverflowError):
        return text

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

    # Placeholder position/altitude only for activities that recorded none (indoor workouts)
    recorded = {local_name(e.tag) for e in activity.iter()}
    keep = {'keep_position': 'Position' in recorded, 'keep_altitude': 'AltitudeMeters' in recorded}

    # Process child elements
    for child in activity:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'Id':
            new_id = ET.SubElement(new_activity, 'Id')
            # Add .000Z format like Garmin
            new_id.text = format_garmin_time(child.text)

        elif tag == 'Creator':
            # Skip Creator - Garmin files don't have this
            pass

        elif tag == 'Lap':
            new_lap = convert_lap_to_garmin_format(child, default_lat, default_lng, **keep)
            new_activity.append(new_lap)

        elif tag == 'Extensions':
            # Skip activity-level extensions
            pass
        else:
            # Copy other elements
            new_activity.append(copy_element_recursive(child))

    return new_activity

def convert_lap_to_garmin_format(lap, default_lat, default_lng, keep_position=False, keep_altitude=False):
    """Convert lap to Garmin format"""
    new_lap = ET.Element('Lap')

    # Copy StartTime with .000Z format
    start_time = lap.get('StartTime')
    if start_time:
        new_lap.set('StartTime', format_garmin_time(start_time))

    # Copy lap-level elements
    for child in lap:
        tag = child.tag.split('}')[-1] if '}' in child.tag else child.tag

        if tag == 'Track':
            new_track = convert_track_to_garmin_format(child, default_lat, default_lng,
                                                       keep_position, keep_altitude)
            new_lap.append(new_track)
        elif tag == 'Extensions':
            # Garmin-style lap extensions: the recorded ns3:LX values, with AvgSpeed computed if missing
            new_ext = ET.SubElement(new_lap, 'Extensions')
            new_ext.append(convert_lap_extensions(lap, child))
        else:
            # Copy other lap elements
            new_lap.append(copy_element_recursive(child))

    return new_lap

def lap_avg_speed(lap):
    """Average speed (m/s, as text) from the lap's DistanceMeters / TotalTimeSeconds, or None"""
    try:
        distance = float(find_child(lap, 'DistanceMeters').text)
        seconds = float(find_child(lap, 'TotalTimeSeconds').text)
    except (AttributeError, TypeError, ValueError):
        return None
    if not (math.isfinite(distance) and math.isfinite(seconds) and seconds > 0):
        return None
    return str(distance / seconds)

def convert_lap_extensions(lap, extensions):
    """ns3:LX with the lap's recorded values in schema order; AvgSpeed from distance/time when not recorded"""
    lx_elem = ET.Element('ns3:LX')
    lx = find_child(extensions, 'LX')
    for name in LX_FIELDS:
        child = find_child(lx, name) if lx is not None else None
        text = child.text if child is not None and child.text else None
        if name == 'AvgSpeed' and text is None:
            text = lap_avg_speed(lap)
        if text is not None:
            ET.SubElement(lx_elem, 'ns3:' + name).text = text
    return lx_elem

def convert_track_to_garmin_format(track, default_lat, default_lng, keep_position=False, keep_altitude=False):
    """Convert track to Garmin format"""
    new_track = ET.Element('Track')

    for trackpoint in track:
        if trackpoint.tag.split('}')[-1] == 'Trackpoint':
            new_trackpoint = convert_trackpoint_to_garmin_format(trackpoint, default_lat, default_lng,
                                                                 keep_position, keep_altitude)
            new_track.append(new_trackpoint)

    return new_track

def convert_trackpoint_to_garmin_format(trackpoint, default_lat, default_lng, keep_position=False, keep_altitude=False):
    """
    Convert trackpoint to exact Garmin format

    keep_position / keep_altitude: the activity recorded GPS / altitude, so copy the trackpoint's own
    values (points without one get none) instead of adding the placeholder to every point.
    """
    new_trackpoint = ET.Element('Trackpoint')

    # Process in TCX schema order: Time, Position, Altitude, Distance, HeartRate, Cadence, Extensions

    # 1. Time with .000Z format
    for child in trackpoint:
        if child.tag.split('}')[-1] == 'Time':
            new_time = ET.SubElement(new_trackpoint, 'Time')
            new_time.text = format_garmin_time(child.text)
            break

    # 2. Position: recorded one, or the placeholder for indoor activities
    if keep_position:
        position = find_child(trackpoint, 'Position')
        if position is not None:
            new_trackpoint.append(copy_element_recursive(position))
    else:
        position_elem = ET.SubElement(new_trackpoint, 'Position')
        lat_elem = ET.SubElement(position_elem, 'LatitudeDegrees')
        lat_elem.text = str(default_lat)
        lng_elem = ET.SubElement(position_elem, 'LongitudeDegrees')
        lng_elem.text = str(default_lng)

    # 3. Altitude: recorded one, or the default for activities without altitude data
    if keep_altitude:
        altitude = find_child(trackpoint, 'AltitudeMeters')
        if altitude is not None:
            ET.SubElement(new_trackpoint, 'AltitudeMeters').text = altitude.text
    else:
        altitude_elem = ET.SubElement(new_trackpoint, 'AltitudeMeters')
        altitude_elem.text = DEFAULT_ALTITUDE

    # 4. Distance (if present in original)
    for child in trackpoint:
        if child.tag.split('}')[-1] == 'DistanceMeters':
            new_distance = ET.SubElement(new_trackpoint, 'DistanceMeters')
            new_distance.text = child.text
            break

    # 5. Heart rate and cadence (if present in original)
    for name in ('HeartRateBpm', 'Cadence'):
        child = find_child(trackpoint, name)
        if child is not None:
            new_trackpoint.append(copy_element_recursive(child))

    # 6. Extensions in Garmin format
    new_ext = ET.SubElement(new_trackpoint, 'Extensions')
    tpx_elem = ET.SubElement(new_ext, 'ns3:TPX')

    extensions = find_child(trackpoint, 'Extensions')
    tpx = find_child(extensions, 'TPX') if extensions is not None else None
    if tpx is not None:
        speed = find_child(tpx, 'Speed')
        watts = find_child(tpx, 'Watts')
        if speed is not None and speed.text:
            # Recorded speed
            ET.SubElement(tpx_elem, 'ns3:Speed').text = speed.text
        elif watts is not None and watts.text:
            # No recorded speed: rough conversion from power (very approximate)
            try:
                speed_value = max(0.1, float(watts.text) / 50.0)
                ET.SubElement(tpx_elem, 'ns3:Speed').text = str(speed_value)
            except (ValueError, TypeError):
                pass
        # Keep running cadence and power, in TCX schema order (Speed, RunCadence, Watts)
        for name in ('RunCadence', 'Watts'):
            child = find_child(tpx, name)
            if child is not None and child.text:
                ET.SubElement(tpx_elem, 'ns3:' + name).text = child.text

    # Without speed or power data the TPX element stays empty, like in the working Garmin file.

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

    # Add the rest of the content. Level 2 gives the same layout as indenting level 1 and then
    # prefixing every line, without touching line breaks inside text values (e.g. Notes).
    ET.indent(root, space="  ", level=2)
    for child in root:
        child_str = ET.tostring(child, encoding='unicode')
        child_lines = child_str.split('\n')
        lines.append('  ' + child_lines[0])
        lines.extend(child_lines[1:-1])  # Skip the trailing indentation line

    lines.append('</TrainingCenterDatabase>')

    return '\n'.join(lines)
