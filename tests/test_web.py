"""Web interface tests: every exported endpoint answers, the static build is complete, and the JS engine tests pass.

Run: python -m pytest -q tests/test_web.py
"""
import shutil
import subprocess
import sys
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from web.app import STATIC, STATIC_ENDPOINTS, app  # noqa: E402

client = TestClient(app)


def test_index_served():
    r = client.get("/")
    assert r.status_code == 200 and "static/main.js" in r.text


@pytest.mark.parametrize("path", STATIC_ENDPOINTS)
def test_endpoint(path):
    r = client.get("/api" + path)
    assert r.status_code == 200, r.text
    assert r.json() is not None


def test_static_build(tmp_path):
    sys.path.insert(0, str(ROOT / "scripts"))
    import build_static
    build_static.build(tmp_path / "site")
    assert (tmp_path / "site" / "index.html").read_text().count("APP_STATIC") == 1
    for path in STATIC_ENDPOINTS:
        assert (tmp_path / "site" / "api" / (path.strip("/") + ".json")).exists()


def test_static_assets_referenced_exist():
    html = (STATIC / "index.html").read_text()
    for name in ("style.css", "main.js"):
        assert f"static/{name}" in html and (STATIC / name).exists()


@pytest.mark.skipif(not shutil.which("node"), reason="node not installed")
def test_js_engine():
    tests = sorted(STATIC.glob("*.test.mjs"))
    for t in tests:
        r = subprocess.run(["node", str(t)], capture_output=True, text=True)
        assert r.returncode == 0, r.stdout + r.stderr


# --- project-specific -----------------------------------------------------------------------------------------------
import json  # noqa: E402

import tcx_core  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"


def test_info_lists_the_converter_defaults():
    info = client.get("/api/info").json()
    assert info["default_lat"] == tcx_core.DEFAULT_LAT and info["changes"] == tcx_core.GARMIN_CHANGES


def test_samples_are_the_committed_synthetic_files():
    for s in client.get("/api/samples").json():
        assert s["text"].encode("utf-8") == (FIXTURES / s["name"]).read_bytes()


def test_convert_runs_the_python_converter():
    files = [("files", ("ride.tcx", (FIXTURES / "indoor_ride.tcx").read_bytes())),
             ("files", ("bad.tcx", b"not xml <<<"))]
    r = client.post("/api/convert", files=files, data={"lat": "-1e-05", "lng": "120"})
    assert r.status_code == 200, r.text
    ok, bad = r.json()
    assert ok["output_name"] == "ride_garmin.tcx"
    assert ok["text"].encode("utf-8") == (FIXTURES / "expected" / "indoor_ride.custom.tcx").read_bytes()
    assert bad["error"].startswith("Invalid TCX file")


@pytest.mark.parametrize("lat,lng", [("abc", "0"), ("91", "0"), ("0", "-181")])
def test_convert_rejects_bad_coordinates(lat, lng):
    r = client.post("/api/convert", files=[("files", ("a.tcx", b"<a/>"))], data={"lat": lat, "lng": lng})
    assert r.status_code == 400


def test_fixtures_are_current():
    """The committed Python reference outputs match what tcx_core produces now (rerun scripts/make_tcx_fixture.py).

    Exact text comparison is safe here: the outputs contain copied text and float division/printing only, no libm."""
    sys.path.insert(0, str(ROOT / "scripts"))
    import make_tcx_fixture
    for path, text in make_tcx_fixture.build().items():
        if path.suffix == ".json":
            assert json.loads(path.read_text("utf-8")) == json.loads(text), path
        else:
            assert path.read_bytes() == text.encode("utf-8"), f"{path} is stale"


def test_samples_contain_no_real_location():
    """Synthetic samples only: GPS points stay within ~1 km of 0 N, 0 E (open sea)."""
    import xml.etree.ElementTree as ET
    for f in FIXTURES.glob("*.tcx"):
        for e in ET.parse(f).getroot().iter():
            if e.tag.endswith(("LatitudeDegrees", "LongitudeDegrees")):
                assert abs(float(e.text)) < 0.01, f
