"""Write the Python reference outputs that the JS port (web/static/tcx_engine.js) is tested against.

Inputs are the synthetic samples tests/fixtures/*.tcx (invented data, no real activity). Outputs:
    tests/fixtures/expected/<name>.tcx       tcx_core.convert_tcx_bytes(input) with the default placeholder position
    tests/fixtures/expected/<name>.custom.tcx  the same with CUSTOM_LAT / CUSTOM_LNG (only for CUSTOM_FOR)
    tests/fixtures/tcx_values.json           Python results for time formatting, float parsing/printing, output
                                             names and the preview summary of each sample

Run: python scripts/make_tcx_fixture.py   (tests/test_web.py checks the committed files are current)
"""
import json
import os
import sys
import xml.etree.ElementTree as ET
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tcx_core import convert_tcx_bytes, format_garmin_time, lap_avg_speed, local_name  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
EXPECTED = FIXTURES / "expected"
CUSTOM_LAT, CUSTOM_LNG = -1e-05, 120.0
CUSTOM_FOR = ["indoor_ride"]

TIMES = [
    "2024-01-15T10:30:00Z", "2024-01-15T10:30:00.123Z", "2024-01-15T10:30:00.1234567Z", "2024-01-15T10:30:00,5Z",
    "2024-01-15T10:30:00+02:00", "2024-01-15T00:30:00+02:00", "2024-12-31T23:59:59-05:30", "2024-02-29T23:00:00-01:00",
    "2023-02-29T10:00:00Z", "2024-01-15", "20240115T103000Z", "20240115T1030", "2024-01-15T10", "2024-01-15 10:30:00",
    "2024-01-15T10:30:00+0200", "2024-01-15T10:30:00+02", "2024-01-15T10:30:00+02:00:30", "2024-01-15T10:30:00+24:00",
    "2024-01-15T24:00:00Z", "2024-01-15T10:60:00Z", "2024-13-01T00:00:00Z", "2024-01-15T10:30:00ZZ", "0001-01-01T00:30:00+01:00",
    "9999-12-31T23:30:00-01:00", "2024-01-15T10:30:00.5+01:00", "2024-01-15T10:30:00.000001-00:00:01.5", "soon", "",
    "2024-1-15T10:30:00Z", "2024-01-15T1030", "2024-01-15T10:30:00 ", "2024/01/15T10:30:00Z", "2024-01-15T103000.25Z",
    "2024-01-15T10:30:00+00.123456", "2024-01-15T10:30:00-00:00:01.25", "2024-01-15T10:30+00:00:00.5",
]
FLOATS = ["150", " 150 ", "1_000", "1__0", "_1", "1_", "12.34", ".5", "5.", ".", "1e3", "1E-2", "-0", "+7", "inf",
          "-Infinity", "nan", "NaN", "abc", "", "0x10", "1e400", "3.5e-07", " 12 "]
REPRS = [30.2672, -97.7431, 0.1, 3.0, 20.0, 0.2468, 1e-05, -1e-05, 0.0001, 1e16, 9999999999999998.0, 1.5e300, 2.5e-300,
         120.0, -0.0, 123456789.123, 1 / 3, 2 / 3 * 1e-5]
LAP_TIMES = [["318.6", "360.0"], ["500", "100"], ["1", "3"], ["10", "0"], ["10", "-5"], ["x", "5"], ["5", "inf"],
             ["1e308", "1e-10"], [" 1_000 ", "7"], ["nan", "1"], [None, "5"], ["0", "60"]]
NAMES = ["ride.tcx", "ride.TCX", "my.ride.tcx", ".tcx", "..tcx", "noext", "a.", ".hidden.tcx", "dir/x.tcx", "x.y/z"]


def py_float(text):
    try:
        return repr(float(text))
    except ValueError:
        return None


def lap_element(distance, seconds):
    lap = ET.Element("Lap")
    ET.SubElement(lap, "TotalTimeSeconds").text = seconds
    ET.SubElement(lap, "DistanceMeters").text = distance
    return lap


def summarize(data):
    """Same numbers as summarize() in web/static/tcx_summary.js."""
    root = ET.fromstring(data)
    s = {"activities": 0, "sports": [], "start": None, "laps": 0, "distance": 0.0, "duration": 0.0, "trackpoints": 0,
         "gps_points": 0, "hr_avg": None, "hr_max": None, "watts_avg": None}
    hr, watts = [], []

    def num(e):
        try:
            v = float(e.text) if e is not None and e.text is not None else None
        except ValueError:
            return None
        return v if v is not None and abs(v) != float("inf") and v == v else None

    def child(e, name):
        return next((c for c in e if local_name(c.tag) == name), None)

    for e in root.iter():
        tag = local_name(e.tag)
        if tag == "Activity":
            s["activities"] += 1
            s["sports"].append(e.get("Sport"))
            if s["start"] is None and child(e, "Id") is not None:
                s["start"] = child(e, "Id").text
        elif tag == "Lap":
            s["laps"] += 1
            d, t = num(child(e, "DistanceMeters")), num(child(e, "TotalTimeSeconds"))
            s["distance"] += d if d is not None else 0
            s["duration"] += t if t is not None else 0
        elif tag == "Trackpoint":
            s["trackpoints"] += 1
            pos = child(e, "Position")
            if pos is not None and None not in (num(child(pos, "LatitudeDegrees")), num(child(pos, "LongitudeDegrees"))):
                s["gps_points"] += 1
            h = child(e, "HeartRateBpm")
            if h is not None and num(child(h, "Value")) is not None:
                hr.append(num(child(h, "Value")))
        elif tag == "Watts" and num(e) is not None:
            watts.append(num(e))
    if hr:
        s["hr_avg"], s["hr_max"] = round(sum(hr) / len(hr), 1), max(hr)
    if watts:
        s["watts_avg"] = round(sum(watts) / len(watts), 1)
    s["distance"], s["duration"] = round(s["distance"], 3), round(s["duration"], 3)
    return s


def build():
    """Return {path: text} for every fixture file."""
    out, summaries = {}, {}
    for src in sorted(FIXTURES.glob("*.tcx")):
        data = src.read_bytes()
        out[EXPECTED / src.name] = convert_tcx_bytes(data)
        if src.stem in CUSTOM_FOR:
            out[EXPECTED / f"{src.stem}.custom.tcx"] = convert_tcx_bytes(data, CUSTOM_LAT, CUSTOM_LNG)
        summaries[src.name] = summarize(data)
    values = {
        "custom": {"lat": CUSTOM_LAT, "lng": CUSTOM_LNG, "files": CUSTOM_FOR},
        "times": [[t, format_garmin_time(t)] for t in TIMES],
        "floats": [[t, py_float(t)] for t in FLOATS],
        "reprs": [[x, repr(x)] for x in REPRS],
        "speeds": [[t, repr(max(0.1, float(t) / 50.0)) if py_float(t) else None] for t in FLOATS],
        "lap_speeds": [[d, t, lap_avg_speed(lap_element(d, t))] for d, t in LAP_TIMES],
        "names": [[n, os.path.splitext(n)[0] + "_garmin.tcx"] for n in NAMES],
        "summaries": summaries,
    }
    out[FIXTURES / "tcx_values.json"] = json.dumps(values, indent=1, ensure_ascii=False) + "\n"
    return out


def main():
    EXPECTED.mkdir(parents=True, exist_ok=True)
    for path, text in build().items():
        path.write_bytes(text.encode("utf-8"))
        print(f"wrote {path.relative_to(ROOT)}")


if __name__ == "__main__":
    main()
