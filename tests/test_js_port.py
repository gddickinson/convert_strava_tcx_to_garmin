"""JS port vs Python on many generated files: seeded mutations of the synthetic samples are converted by
tcx_core.convert_tcx_bytes and by web/static/tcx_engine.js (node); outputs (or both failing) must agree exactly.

Run: python -m pytest -q tests/test_js_port.py
"""
import json
import random
import re
import shutil
import subprocess
import sys
import zipfile
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from tcx_core import convert_tcx_bytes  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
TEXTS = ["", " ", "1e-5", "2024-01-15T10:30:00+01:00", "150", "a &amp; b", "x\ny", "&#x1F600;", "<![CDATA[]]>",
         " ", "\x85", "nan", " 12 ", "1_0", "2024-01-15T10:30:00.5-05:30", "-3.25"]
SNIPS = ["<!-- c -->", "<?pi x?>", "<Notes>a\n  b</Notes>",
         "<Position><LatitudeDegrees>0.001</LatitudeDegrees><LongitudeDegrees>0.002</LongitudeDegrees></Position>",
         "<AltitudeMeters>3</AltitudeMeters>", "<Cadence/>", "<HeartRateBpm><Value>99</Value></HeartRateBpm>",
         "<Extensions><ns3:TPX><ns3:Speed>1</ns3:Speed><ns3:RunCadence>80</ns3:RunCadence></ns3:TPX></Extensions>",
         '<q:z xmlns:q="urn:q" q:a="1&#10;&#9;"/>', '<w:Watts xmlns:w="urn:w">7</w:Watts>',
         '<x xml:lang="en" xmlns:dc="http://purl.org/dc/elements/1.1/" dc:t="1"/>', "<", "&", "\r\n"]


def mutated(n, seed=7):
    rnd = random.Random(seed)
    srcs = [(FIXTURES / f).read_text("utf-8") for f in ("indoor_ride.tcx", "outdoor_run.tcx", "edge_cases.tcx")]
    tail = "</Track></Lap></Activity></Activities></TrainingCenterDatabase>"
    srcs = [srcs[0][:4000] + tail, srcs[1][:4000] + tail, srcs[2]]
    for _ in range(n):
        s = rnd.choice(srcs)
        for _ in range(rnd.randint(1, 4)):
            k = rnd.choice([m.end() for m in re.finditer(">", s)][1:-1])
            if rnd.random() < 0.5:
                s = s[:k] + rnd.choice(TEXTS) + s[s.index("<", k):]
            else:
                s = s[:k] + rnd.choice(SNIPS) + s[k:]
        yield s


def node(script, *args):
    r = subprocess.run(["node", "--input-type=module", "-e", script, *args], capture_output=True, text=True, cwd=ROOT)
    assert r.returncode == 0, r.stdout + r.stderr
    return r.stdout


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_matches_python_on_mutated_files(tmp_path):
    cases = []
    for s in mutated(800):
        try:
            out = convert_tcx_bytes(s.encode("utf-8"))
        except ValueError:
            out = None
        cases.append([s, out])
    data = tmp_path / "cases.json"
    data.write_text(json.dumps(cases))
    res = json.loads(node("""
import { readFileSync } from 'node:fs';
import { convertTcx } from './web/static/tcx_engine.js';
const cases = JSON.parse(readFileSync(process.argv[1], 'utf8')); const bad = []; let valid = 0;
cases.forEach(([s, want], i) => { let got = null; try { got = convertTcx(new TextEncoder().encode(s)); } catch (e) {}
  if (want !== null) valid++; if (got !== want) bad.push(i); });
console.log(JSON.stringify({ bad, valid }));""", str(data)))
    assert res["valid"] > 300, res
    assert res["bad"] == [], f"{len(res['bad'])} differ, first: {cases[res['bad'][0]][0][:300]!r}"


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_zip_writer_output_reads_with_zipfile(tmp_path):
    out = tmp_path / "all.zip"
    node("""
import { writeFileSync, readFileSync } from 'node:fs';
import { makeZip } from './web/static/zip.js';
const big = readFileSync('tests/fixtures/expected/outdoor_run.tcx');
writeFileSync(process.argv[1], makeZip([{ name: 'ride_garmin.tcx', data: 'abc' }, { name: 'café_garmin.tcx', data: new Uint8Array(big) }]));""",
         str(out))
    with zipfile.ZipFile(out) as z:
        assert z.testzip() is None
        assert z.namelist() == ["ride_garmin.tcx", "café_garmin.tcx"]
        assert z.read("café_garmin.tcx") == (FIXTURES / "expected" / "outdoor_run.tcx").read_bytes()
