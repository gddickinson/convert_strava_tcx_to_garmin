"""Tests for tcx_converter.py using sample TCX fragments."""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tcx_converter import (
    clean_tcx_for_garmin,
    convert_tcx_bytes,
    create_garmin_root,
    copy_element_recursive,
    add_garmin_author_section,
    DEFAULT_LAT,
    DEFAULT_LNG,
    DEFAULT_ALTITUDE,
)

NS = {"t": "http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2",
      "x": "http://www.garmin.com/xmlschemas/ActivityExtension/v2"}


def tcx(activity_body, sport="Biking"):
    """A minimal TCX document wrapping one Activity's children."""
    return (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2" '
        'xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">'
        f'<Activities><Activity Sport="{sport}">{activity_body}</Activity></Activities>'
        '</TrainingCenterDatabase>'
    )


def trackpoint(inner):
    return f'<Id>2024-01-15T10:30:00Z</Id><Lap StartTime="2024-01-15T10:30:00Z"><Track><Trackpoint>{inner}</Trackpoint></Track></Lap>'


def converted(text):
    """Convert TCX text and parse the result back (output declares the default Garmin namespaces)."""
    return ET.fromstring(convert_tcx_bytes(text.encode("utf-8")))


SAMPLE_TCX = """\
<?xml version="1.0" encoding="UTF-8"?>
<TrainingCenterDatabase xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2">
  <Activities>
    <Activity Sport="Biking">
      <Id>2024-01-15T10:30:00Z</Id>
      <Lap StartTime="2024-01-15T10:30:00Z">
        <TotalTimeSeconds>3600</TotalTimeSeconds>
        <DistanceMeters>25000</DistanceMeters>
        <Track>
          <Trackpoint>
            <Time>2024-01-15T10:30:00Z</Time>
            <DistanceMeters>0</DistanceMeters>
          </Trackpoint>
          <Trackpoint>
            <Time>2024-01-15T10:30:10Z</Time>
            <DistanceMeters>100</DistanceMeters>
          </Trackpoint>
        </Track>
        <Extensions>
          <ns3:LX xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2">
            <ns3:AvgSpeed>6.94</ns3:AvgSpeed>
          </ns3:LX>
        </Extensions>
      </Lap>
    </Activity>
  </Activities>
</TrainingCenterDatabase>
"""


class TestCreateGarminRoot(unittest.TestCase):
    def test_root_tag(self):
        root = create_garmin_root()
        self.assertEqual(root.tag, "TrainingCenterDatabase")

    def test_namespace_attributes_present(self):
        root = create_garmin_root()
        self.assertIn("xmlns", root.attrib)


class TestCopyElementRecursive(unittest.TestCase):
    def test_preserves_tag_and_text(self):
        elem = ET.Element("Foo")
        elem.text = "bar"
        copy = copy_element_recursive(elem)
        self.assertEqual(copy.tag, "Foo")
        self.assertEqual(copy.text, "bar")

    def test_preserves_children(self):
        parent = ET.Element("Parent")
        child = ET.SubElement(parent, "Child")
        child.text = "data"
        copy = copy_element_recursive(parent)
        children = list(copy)
        self.assertEqual(len(children), 1)
        self.assertEqual(children[0].text, "data")


class TestAddGarminAuthor(unittest.TestCase):
    def test_author_section_added(self):
        root = ET.Element("Root")
        add_garmin_author_section(root)
        author = root.find("Author")
        self.assertIsNotNone(author)
        name = author.find("Name")
        self.assertEqual(name.text, "Connect Api")


class TestCleanTcxForGarmin(unittest.TestCase):
    def setUp(self):
        self.tmpdir = tempfile.mkdtemp()
        self.input_file = os.path.join(self.tmpdir, "test_input.tcx")
        with open(self.input_file, "w") as f:
            f.write(SAMPLE_TCX)

    def test_creates_output_file(self):
        output_file = os.path.join(self.tmpdir, "test_output.tcx")
        result = clean_tcx_for_garmin(self.input_file, output_file)
        self.assertEqual(result, output_file)
        self.assertTrue(os.path.exists(output_file))

    def test_default_output_filename(self):
        result = clean_tcx_for_garmin(self.input_file)
        expected = os.path.join(self.tmpdir, "test_input_garmin.tcx")
        self.assertEqual(result, expected)
        self.assertTrue(os.path.exists(expected))

    def test_output_contains_garmin_structure(self):
        output_file = os.path.join(self.tmpdir, "test_output.tcx")
        clean_tcx_for_garmin(self.input_file, output_file)
        with open(output_file) as f:
            content = f.read()
        self.assertIn("TrainingCenterDatabase", content)
        self.assertIn("Connect Api", content)
        self.assertIn('Sport="Other"', content)

    def test_timestamp_format(self):
        output_file = os.path.join(self.tmpdir, "test_output.tcx")
        clean_tcx_for_garmin(self.input_file, output_file)
        with open(output_file) as f:
            content = f.read()
        # Should contain .000Z formatted timestamps
        self.assertIn(".000Z", content)

    def test_position_added_to_trackpoints(self):
        output_file = os.path.join(self.tmpdir, "test_output.tcx")
        clean_tcx_for_garmin(self.input_file, output_file)
        with open(output_file) as f:
            content = f.read()
        self.assertIn("LatitudeDegrees", content)
        self.assertIn("LongitudeDegrees", content)

    def test_invalid_xml_raises(self):
        bad_file = os.path.join(self.tmpdir, "bad.tcx")
        with open(bad_file, "w") as f:
            f.write("not xml at all <<<<")
        with self.assertRaises(ValueError):
            clean_tcx_for_garmin(bad_file)

    def test_custom_coordinates(self):
        output_file = os.path.join(self.tmpdir, "test_output.tcx")
        clean_tcx_for_garmin(self.input_file, output_file, default_lat=51.5074, default_lng=-0.1278)
        with open(output_file) as f:
            content = f.read()
        self.assertIn("51.5074", content)
        self.assertIn("-0.1278", content)


class TestPowerToSpeed(unittest.TestCase):
    def test_one_speed_per_trackpoint(self):
        # Regression: a second <ns3:Speed>0.1</ns3:Speed> was appended after every power-based speed
        out = converted(tcx(trackpoint(
            "<Time>2024-01-15T10:30:00Z</Time><Extensions><ns3:TPX><ns3:Watts>150</ns3:Watts></ns3:TPX></Extensions>")))
        speeds = [e.text for e in out.iter("{%s}Speed" % NS["x"])]
        self.assertEqual(speeds, ["3.0"])


class TestMultiLineText(unittest.TestCase):
    def test_notes_keep_their_line_breaks_exactly(self):
        # Regression: every line of the output was re-indented, which also inserted spaces into
        # multi-line text such as activity Notes
        notes = "First line\nsecond line\n  third, indented"
        out = converted(tcx(f"<Id>2024-01-15T10:30:00Z</Id><Notes>{notes}</Notes>"))
        self.assertEqual(out.find(".//t:Notes", NS).text, notes)


class TestTimestamps(unittest.TestCase):
    def test_utc_offsets_are_converted_to_utc(self):
        # Regression: '23:59:30+02:00' was written as '23:59:30.000Z' (two hours wrong)
        out = converted(tcx(trackpoint("<Time>2024-12-31T23:59:30+02:00</Time>")
                            .replace("2024-01-15T10:30:00Z", "2025-01-01T05:30:05.5-05:30")))
        self.assertEqual(out.find(".//t:Trackpoint/t:Time", NS).text, "2024-12-31T21:59:30.000Z")
        self.assertEqual(out.find(".//t:Lap", NS).get("StartTime"), "2025-01-01T11:00:05.000Z")
        self.assertEqual(out.find(".//t:Id", NS).text, "2025-01-01T11:00:05.000Z")

    def test_utc_and_unparseable_times_unchanged(self):
        out = converted(tcx(trackpoint("<Time>soon</Time>")))
        self.assertEqual(out.find(".//t:Id", NS).text, "2024-01-15T10:30:00.000Z")
        self.assertEqual(out.find(".//t:Trackpoint/t:Time", NS).text, "soon")


class TestRecordedGps(unittest.TestCase):
    OUTDOOR = ('<Id>2024-01-15T10:30:00Z</Id><Lap StartTime="2024-01-15T10:30:00Z"><Track>'
               '<Trackpoint><Time>2024-01-15T10:30:00Z</Time>'
               '<Position><LatitudeDegrees>0.0012345</LatitudeDegrees><LongitudeDegrees>-0.0023456</LongitudeDegrees></Position>'
               '<AltitudeMeters>5.5</AltitudeMeters></Trackpoint>'
               '<Trackpoint><Time>2024-01-15T10:30:01Z</Time></Trackpoint>'
               '</Track></Lap>')

    def test_recorded_positions_and_altitude_are_kept(self):
        # Regression: every trackpoint got the dummy Austin position and altitude, even outdoor
        # activities with real GPS, so their route was lost
        tps = converted(tcx(self.OUTDOOR, sport="Running")).findall(".//t:Trackpoint", NS)
        self.assertEqual(tps[0].find("t:Position/t:LatitudeDegrees", NS).text, "0.0012345")
        self.assertEqual(tps[0].find("t:Position/t:LongitudeDegrees", NS).text, "-0.0023456")
        self.assertEqual(tps[0].find("t:AltitudeMeters", NS).text, "5.5")
        # a point without a fix in a GPS activity gets no made-up position
        self.assertIsNone(tps[1].find("t:Position", NS))
        self.assertIsNone(tps[1].find("t:AltitudeMeters", NS))

    def test_indoor_activities_still_get_the_placeholder(self):
        tp = converted(tcx(trackpoint("<Time>2024-01-15T10:30:00Z</Time>"))).find(".//t:Trackpoint", NS)
        self.assertEqual(tp.find("t:Position/t:LatitudeDegrees", NS).text, str(DEFAULT_LAT))
        self.assertEqual(tp.find("t:AltitudeMeters", NS).text, DEFAULT_ALTITUDE)


class TestSensorData(unittest.TestCase):
    def convert_point(self, inner):
        return converted(tcx(trackpoint("<Time>2024-01-15T10:30:00Z</Time>" + inner))).find(".//t:Trackpoint", NS)

    def test_heart_rate_cadence_and_power_are_kept(self):
        # Regression: trackpoint heart rate, cadence and power were dropped although the README
        # lists them as preserved
        tp = self.convert_point("<DistanceMeters>10</DistanceMeters><HeartRateBpm><Value>150</Value></HeartRateBpm>"
                                "<Cadence>85</Cadence><Extensions><ns3:TPX><ns3:Watts>150</ns3:Watts></ns3:TPX></Extensions>")
        self.assertEqual(tp.find("t:HeartRateBpm/t:Value", NS).text, "150")
        self.assertEqual(tp.find("t:Cadence", NS).text, "85")
        tpx = tp.find("t:Extensions/x:TPX", NS)
        self.assertEqual([(c.tag.split("}")[1], c.text) for c in tpx], [("Speed", "3.0"), ("Watts", "150")])
        # TCX schema order
        self.assertEqual([c.tag.split("}")[1] for c in tp],
                         ["Time", "Position", "AltitudeMeters", "DistanceMeters", "HeartRateBpm", "Cadence", "Extensions"])

    def test_recorded_speed_is_kept_instead_of_the_estimate(self):
        tp = self.convert_point("<Extensions><ns3:TPX><ns3:Speed>4.2</ns3:Speed><ns3:RunCadence>88</ns3:RunCadence>"
                                "<ns3:Watts>300</ns3:Watts></ns3:TPX></Extensions>")
        tpx = tp.find("t:Extensions/x:TPX", NS)
        self.assertEqual([(c.tag.split("}")[1], c.text) for c in tpx], [("Speed", "4.2"), ("RunCadence", "88"), ("Watts", "300")])


class TestLapExtensions(unittest.TestCase):
    def lx(self, lap_inner):
        out = converted(tcx(f'<Id>2024-01-15T10:30:00Z</Id><Lap StartTime="2024-01-15T10:30:00Z">{lap_inner}</Lap>'))
        lx = out.find(".//t:Lap/t:Extensions/x:LX", NS)
        return None if lx is None else [(c.tag.split("}")[1], c.text) for c in lx]

    def test_recorded_lap_values_are_kept(self):
        # Regression: every lap's extensions were replaced by a fixed AvgSpeed of 4.98 m/s
        self.assertEqual(self.lx("<TotalTimeSeconds>100</TotalTimeSeconds><DistanceMeters>500</DistanceMeters>"
                                 "<Extensions><ns3:LX><ns3:MaxWatts>300</ns3:MaxWatts><ns3:AvgSpeed>6.5</ns3:AvgSpeed>"
                                 "<ns3:AvgWatts>180</ns3:AvgWatts></ns3:LX></Extensions>"),
                         [("AvgSpeed", "6.5"), ("AvgWatts", "180"), ("MaxWatts", "300")])

    def test_missing_avg_speed_is_computed_from_distance_and_time(self):
        self.assertEqual(self.lx("<TotalTimeSeconds>360.0</TotalTimeSeconds><DistanceMeters>318.6</DistanceMeters>"
                                 "<Extensions><ns3:LX><ns3:AvgWatts>125</ns3:AvgWatts></ns3:LX></Extensions>"),
                         [("AvgSpeed", str(318.6 / 360.0)), ("AvgWatts", "125")])

    def test_no_speed_without_distance_or_time(self):
        self.assertEqual(self.lx("<TotalTimeSeconds>0</TotalTimeSeconds><DistanceMeters>10</DistanceMeters>"
                                 "<Extensions/>"), [])
        self.assertIsNone(self.lx("<TotalTimeSeconds>60</TotalTimeSeconds>"))


if __name__ == "__main__":
    unittest.main()
