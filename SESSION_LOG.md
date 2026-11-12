# Session log

## 2026-11-11: web interface, static site and bug fixes (branch `web-interface`)
- Split the conversion out of `tcx_converter.py` into `tcx_core.py` (`convert_tcx_bytes`: bytes in, Garmin XML text
  out); the CLI re-exports the names, output byte-identical before/after. Added the `.gitignore` the docs described.
- Bugs fixed (each in its own "Fix ..." commit with regression tests in `test_tcx_converter.py`):
  - every trackpoint with power got a second `<ns3:Speed>0.1</ns3:Speed>` (truth test on an Element; also a
    Python 3.12 DeprecationWarning);
  - multi-line text (e.g. activity Notes) got two extra spaces after each line break from the output indentation;
  - times with a UTC offset (`+02:00`) were labelled `Z` without being converted to UTC;
  - outdoor activities lost their recorded GPS route and altitude (every point got the Austin placeholder); now the
    placeholder is used only for activities without positions/altitude, as the README describes;
  - trackpoint heart rate, cadence and power were dropped (README says preserved) and a recorded speed was replaced by
    the power estimate; now kept in TCX schema order.
- Docs: README said Python 3.6+, but `ET.indent` needs 3.9+; README/CLI change list updated for the fixes.
- Web: `web/` (FastAPI + ES modules, port 8153), `run_web.py`, `requirements-web.txt`, `scripts/build_static.py`,
  `scripts/screenshots.py`, `.github/workflows/pages.yml` (tests + Pages on push to main; now also runs
  `test_tcx_converter.py`). The static site IS the converter: drop TCX files, converted in the browser by
  `tcx_engine.js` (never uploaded), preview (route SVG + distance, duration, laps, HR, power), per-file download or a
  zip (own tiny zip writer). Local app adds "Check with the Python converter" (POST /api/convert, byte comparison).
- JS vs Python: synthetic samples in `tests/fixtures/` (invented data; GPS loop in the sea at 0 N 0 E, edge-case
  file with CRLF/BOM/offsets/CDATA/namespaces); `scripts/make_tcx_fixture.py` writes the Python outputs; node test
  byte-identical on all samples (+ custom placeholder), plus Python-semantics tables (times, floats, names) and the
  preview summary. `tests/test_js_port.py`: 800 seeded mutated files agree (outputs or both rejected); ad-hoc fuzzing
  during development: 30,000 timestamps and 4,500 files, 0 differences after fixing two port gaps.
- Not ported: ISO week dates (`2024-W03-1`) in `fromisoformat` (TCX never uses them; JS leaves them unchanged).
- Open at first (cosmetic, not changed): the output indentation is uneven; kept so the output stays byte-identical.

## 2026-11-11 (later): follow-up fixes requested via the lead
- Lap extensions keep their recorded ns3:LX values (AvgSpeed, AvgWatts, MaxWatts, ... in schema order); a missing
  AvgSpeed is computed as DistanceMeters / TotalTimeSeconds (omitted if not computable). The fixed 4.98 m/s constant
  (DEFAULT_AVG_SPEED) is gone. JS port updated; edge-case sample gained a lap without AvgSpeed; fixtures regenerated.
- Batch mode skips earlier `*_garmin.tcx` outputs (reported as skipped) and processes files in sorted order; a
  single-file conversion refuses to write over its own input.
- All checks re-run: pytest 42 passed (tests/ + test_tcx_converter.py), node 144 checks byte-identical, screenshots
  static + local all ok, Python check in the local app byte-identical.
