"""FastAPI web app for the Strava TCX -> Garmin converter: serves the front end in static/ and the JSON API under /api.

Run with `python run_web.py` (http://127.0.0.1:8153, local only). `scripts/build_static.py` exports every path in
STATIC_ENDPOINTS to JSON for the GitHub Pages site, so keep that list in step with the GET routes below. The static
site converts files in the browser (static/tcx_engine.js, a byte-identical port of tcx_core.py); the local app also
offers POST /api/convert, which runs the Python converter itself.
"""
import sys
from pathlib import Path
from typing import List

from fastapi import FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

import tcx_core  # noqa: E402
from tcx_converter import garmin_output_name  # noqa: E402

STATIC = Path(__file__).resolve().parent / "static"
FIXTURES = ROOT / "tests" / "fixtures"
SAMPLES = {  # synthetic test files (invented data), offered as "try a sample"
    "outdoor_run.tcx": "Outdoor run: two laps of a loop in the open sea near 0° N, 0° E",
    "indoor_ride.tcx": "Indoor ride: power, heart rate and cadence, no GPS",
}
MAX_UPLOAD_BYTES = 50 * 1024 * 1024
DESCRIPTION = ("Converts Strava-exported TCX files to be compatible with Garmin Connect import. "
               "Perfect for getting your Peloton workouts from Strava into Garmin Connect.")

app = FastAPI(title="Strava TCX to Garmin")
app.mount("/static", StaticFiles(directory=STATIC), name="static")


@app.get("/", include_in_schema=False)
def index():
    return FileResponse(STATIC / "index.html")


@app.get("/api/info")
def info():
    """Description, the converter's defaults and the list of changes it makes (from tcx_core)."""
    return {
        "title": "Strava TCX to Garmin",
        "description": DESCRIPTION,
        "default_lat": tcx_core.DEFAULT_LAT,
        "default_lng": tcx_core.DEFAULT_LNG,
        "default_place": "Austin, TX",
        "default_altitude": tcx_core.DEFAULT_ALTITUDE,
        "default_avg_speed": tcx_core.DEFAULT_AVG_SPEED,
        "changes": tcx_core.GARMIN_CHANGES,
        "samples": len(SAMPLES),
    }


@app.get("/api/samples")
def samples():
    """The synthetic sample files (text) for the "try a sample" button."""
    return [{"name": n, "label": label, "text": (FIXTURES / n).read_bytes().decode("utf-8")}
            for n, label in SAMPLES.items()]


def _coordinate(text, name, limit):
    try:
        value = float(text)
    except ValueError:
        raise HTTPException(400, f"{name} must be a number")
    if not -limit <= value <= limit:
        raise HTTPException(400, f"{name} must be between -{limit} and {limit}")
    return value


@app.post("/api/convert")
async def convert(files: List[UploadFile] = File(...), lat: str = Form(str(tcx_core.DEFAULT_LAT)),
                  lng: str = Form(str(tcx_core.DEFAULT_LNG))):
    """Convert uploaded TCX files with the Python converter (tcx_core.convert_tcx_bytes); nothing is stored."""
    lat_v, lng_v = _coordinate(lat, "Latitude", 90), _coordinate(lng, "Longitude", 180)
    results = []
    for f in files:
        data = await f.read()
        name = Path(f.filename or "activity.tcx").name
        item = {"name": name, "output_name": garmin_output_name(name)}
        if len(data) > MAX_UPLOAD_BYTES:
            item["error"] = "File too large for the web app (50 MB)."
        else:
            try:
                item["text"] = tcx_core.convert_tcx_bytes(data, lat_v, lng_v)
            except ValueError as e:
                item["error"] = str(e)
        results.append(item)
    return results


# GET paths (without the /api prefix) written to the static site as api/<path>.json.
STATIC_ENDPOINTS = ["/info", "/samples"]
