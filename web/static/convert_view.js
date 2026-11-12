// Rendering for the convert page: one card per file with the preview (summary + route SVG) and its actions.
import { esc } from './core.js';
import { routeSvg, fmtDuration, fmtDistance } from './tcx_summary.js';

const fact = (label, value) => `<div>${esc(label)}<b>${esc(value)}</b></div>`;

export function fileCard(f, i, coords) {
  const s = f.summary;
  if (f.error) {
    return `<article class="panel file"><div><h3>${esc(f.name)}</h3><p class="err">${esc(f.error)}</p>
      <p class="small mute">Garmin and this converter need a well-formed TCX (XML) file. Try exporting it from Strava again.</p></div></article>`;
  }
  const facts = [
    fact('Sport (in file)', s.sports.join(', ') || '?'),
    fact('Distance', fmtDistance(s.distance)),
    fact('Duration', s.duration ? fmtDuration(s.duration) : '?'),
    fact('Laps', s.laps),
    fact('Trackpoints', s.trackpoints),
    fact('GPS points', s.gps_points),
  ];
  if (s.hr_avg !== null) facts.push(fact('Heart rate', `${s.hr_avg} avg · ${s.hr_max} max`));
  if (s.watts_avg !== null) facts.push(fact('Power', `${s.watts_avg} W avg`));
  const svg = routeSvg(s.route, { label: `Route of ${f.name}` });
  const map = svg || `<div class="noroute">No GPS positions in this file (indoor workout). The converted file gets the
    placeholder position <b>${esc(coords)}</b> on every trackpoint, as Garmin Connect expects a position.</div>`;
  const kb = (new TextEncoder().encode(f.out).length / 1024).toFixed(1);
  const preview = f.out.split('\n').slice(0, 60).join('\n');
  return `<article class="panel file"><div>
      <h3>${esc(f.name)}</h3><p class="small mute">→ ${esc(f.outName)} · ${kb} KB${s.start ? ' · started ' + esc(s.start) : ''}</p>
      <div class="facts">${facts.join('')}</div>
      <div class="bar"><button data-dl="${i}">Download ${esc(f.outName)}</button></div>
      <div class="pyres" id="py-${i}" aria-live="polite">${f.py || ''}</div>
      <details><summary>Show the start of the converted file</summary><pre>${esc(preview)}</pre></details>
    </div><div>${map}</div></article>`;
}
