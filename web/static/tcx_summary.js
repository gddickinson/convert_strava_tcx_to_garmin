// Preview of a TCX file read in the browser: summary numbers and a route SVG. Pure functions (node-tested against
// the same summary computed in Python by scripts/make_tcx_fixture.py).
import { parseXml, iter, getAttr } from './tcx_xml.js';
import { pyFloat } from './tcx_pyfmt.js';
import { localName, findChild } from './tcx_engine.js';

const num = e => (e && e.text != null ? pyFloat(e.text) : null);
const finite = x => x !== null && Number.isFinite(x);
const round = (x, d) => (x === null ? null : Math.round(x * 10 ** d) / 10 ** d);

// Summary of a parsed TCX root (or bytes/text): sports, start, laps, distance (m, sum of lap DistanceMeters),
// duration (s, sum of lap TotalTimeSeconds), trackpoints, GPS points, heart rate and power where recorded.
export function summarize(input) {
  const root = typeof input === 'object' && input.tag ? input : parseXml(input);
  const s = { activities: 0, sports: [], start: null, laps: 0, distance: 0, duration: 0, trackpoints: 0,
    gps_points: 0, hr_avg: null, hr_max: null, watts_avg: null, route: [] };
  const hr = [], watts = [];
  for (const e of iter(root)) {
    const tag = localName(e.tag);
    if (tag === 'Activity') {
      s.activities++;
      s.sports.push(getAttr(e, 'Sport'));
      const id = findChild(e, 'Id');
      if (s.start === null && id) s.start = id.text;
    } else if (tag === 'Lap') {
      s.laps++;
      const d = num(findChild(e, 'DistanceMeters')), t = num(findChild(e, 'TotalTimeSeconds'));
      if (finite(d)) s.distance += d;
      if (finite(t)) s.duration += t;
    } else if (tag === 'Trackpoint') {
      s.trackpoints++;
      const pos = findChild(e, 'Position');
      if (pos) {
        const la = num(findChild(pos, 'LatitudeDegrees')), lo = num(findChild(pos, 'LongitudeDegrees'));
        if (finite(la) && finite(lo)) { s.gps_points++; s.route.push([la, lo]); }
      }
      const h = findChild(e, 'HeartRateBpm');
      const hv = h ? num(findChild(h, 'Value')) : null;
      if (finite(hv)) hr.push(hv);
    } else if (tag === 'Watts' && finite(num(e))) watts.push(num(e));
  }
  if (hr.length) { s.hr_avg = round(hr.reduce((a, b) => a + b, 0) / hr.length, 1); s.hr_max = Math.max(...hr); }
  if (watts.length) s.watts_avg = round(watts.reduce((a, b) => a + b, 0) / watts.length, 1);
  s.distance = round(s.distance, 3); s.duration = round(s.duration, 3);
  return s;
}

export function fmtDuration(sec) {
  const t = Math.round(sec), h = Math.floor(t / 3600), m = Math.floor((t % 3600) / 60), x = t % 60;
  return (h ? `${h}:${String(m).padStart(2, '0')}` : `${m}`) + `:${String(x).padStart(2, '0')}`;
}
export const fmtDistance = m => (m >= 1000 ? `${(m / 1000).toFixed(2)} km` : `${Math.round(m)} m`);

// Route as an SVG polyline (equirectangular projection, north up), or null when the file has no GPS.
export function routeSvg(route, { w = 320, h = 220, pad = 14, label = 'Route' } = {}) {
  if (route.length < 2) return null;
  const lat0 = route.reduce((a, p) => a + p[0], 0) / route.length, k = Math.cos(lat0 * Math.PI / 180);
  const xy = route.map(([la, lo]) => [lo * k, -la]);
  const xs = xy.map(p => p[0]), ys = xy.map(p => p[1]);
  const x0 = Math.min(...xs), y0 = Math.min(...ys);
  const span = Math.max(Math.max(...xs) - x0, Math.max(...ys) - y0) || 1e-9;
  const sc = Math.min(w - 2 * pad, h - 2 * pad) / span;
  const ox = (w - (Math.max(...xs) - x0) * sc) / 2, oy = (h - (Math.max(...ys) - y0) * sc) / 2;
  const pts = xy.map(([x, y]) => [ox + (x - x0) * sc, oy + (y - y0) * sc]);
  const path = pts.map(p => p[0].toFixed(1) + ',' + p[1].toFixed(1)).join(' ');
  const [sx, sy] = pts[0], [ex, ey] = pts[pts.length - 1];
  return `<svg class="route" viewBox="0 0 ${w} ${h}" role="img" aria-label="${label}">
    <polyline points="${path}" fill="none" stroke="var(--accent)" stroke-width="2.5" stroke-linejoin="round" stroke-linecap="round"/>
    <circle cx="${sx.toFixed(1)}" cy="${sy.toFixed(1)}" r="5" fill="var(--accent3)"><title>start</title></circle>
    <circle cx="${ex.toFixed(1)}" cy="${ey.toFixed(1)}" r="4" fill="none" stroke="var(--accent2)" stroke-width="2"><title>end</title></circle></svg>`;
}
