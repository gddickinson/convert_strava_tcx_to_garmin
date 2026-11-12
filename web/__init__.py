"""Web interface for the Strava TCX -> Garmin converter (FastAPI + plain ES-module front end).

Contents:
    app     - FastAPI app: static front end, GET /api/info, /api/samples, POST /api/convert (runs tcx_core)
    static/ - front end; tcx_engine.js (+ tcx_xml.js, tcx_pyfmt.js) is the JS port of tcx_core.py that converts
              files in the browser on the static GitHub Pages site; tcx_summary.js builds the preview; zip.js
              writes the "download all" zip
"""
