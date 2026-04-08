"""Tests for tcx_converter.py using sample TCX fragments."""

import os
import tempfile
import unittest
import xml.etree.ElementTree as ET

from tcx_converter import (
    clean_tcx_for_garmin,
    create_garmin_root,
    copy_element_recursive,
    add_garmin_author_section,
    DEFAULT_LAT,
    DEFAULT_LNG,
    DEFAULT_ALTITUDE,
)

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


if __name__ == "__main__":
    unittest.main()
