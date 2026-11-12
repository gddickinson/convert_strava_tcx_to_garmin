// Convert page: drop TCX files, convert them in the browser with the JS port of tcx_core.py, preview and download.
// On the local app, "Check with Python" also runs the real Python converter and compares the outputs byte for byte.
import { route, app, api, isStatic, esc, download, $, needsServer } from './core.js';
import { convertTcx } from './tcx_engine.js';
import { summarize } from './tcx_summary.js';
import { parseXml } from './tcx_xml.js';
import { pyFloat, pyRepr, garminOutputName } from './tcx_pyfmt.js';
import { makeZip, uniqueNames } from './zip.js';
import { fileCard } from './convert_view.js';

const TCX_TYPE = 'application/vnd.garmin.tcx+xml';
let entries = [];   // { name, bytes, out, outName, summary, error, py }

function coordsFrom(info) {
  const lat = pyFloat($('#lat').value), lng = pyFloat($('#lng').value);
  const ok = lat !== null && lng !== null && Math.abs(lat) <= 90 && Math.abs(lng) <= 180;
  $('#coord-err').textContent = ok ? '' : 'Latitude must be a number from -90 to 90 and longitude from -180 to 180.';
  return ok ? { lat, lng } : { lat: info.default_lat, lng: info.default_lng };
}

function convertOne(e, c) {
  try {
    const root = parseXml(e.bytes);
    e.summary = summarize(root);
    e.out = convertTcx(e.bytes, c.lat, c.lng);
    e.error = null;
  } catch (err) { e.error = err.message; e.out = null; }
  e.outName = garminOutputName(e.name);
  e.py = '';
}

function render(info) {
  const c = coordsFrom(info), good = entries.filter(e => e.out);
  const coords = `${pyRepr(c.lat)}, ${pyRepr(c.lng)}`;
  $('#files').innerHTML = entries.map((e, i) => fileCard(e, i, coords)).join('');
  $('#all').hidden = good.length < 2;
  $('#pycheck').hidden = isStatic() || !good.length;
  $('#clear').hidden = !entries.length;
  $('#count').textContent = entries.length
    ? `${good.length} of ${entries.length} file${entries.length > 1 ? 's' : ''} converted in your browser.` : '';
}

async function addFiles(list, info) {
  const c = coordsFrom(info);
  for (const f of list) {
    const e = { name: f.name, bytes: f.bytes || new Uint8Array(await f.arrayBuffer()) };
    convertOne(e, c);
    entries.push(e);
  }
  render(info);
}

async function pythonCheck(info) {
  const c = coordsFrom(info), fd = new FormData();
  const sent = entries.filter(e => e.out);
  sent.forEach(e => fd.append('files', new Blob([e.bytes]), e.name));
  fd.append('lat', pyRepr(c.lat)); fd.append('lng', pyRepr(c.lng));
  $('#pycheck').disabled = true;
  try {
    const res = await api('/convert', { body: fd });
    res.forEach((r, k) => {
      const e = sent[k];
      e.py = r.error ? `<span class="err">Python: ${esc(r.error)}</span>`
        : r.text === e.out ? '<span class="ok">✓ Python converter output is byte-identical.</span>'
          : '<span class="err">Python output differs from the browser output (please report this).</span>';
      e.pyText = r.text;
    });
  } catch (err) { $('#count').textContent = err.message; }
  $('#pycheck').disabled = false;
  render(info);
}

route('convert', async (args, query) => {
  const info = await api('/info');
  entries = [];
  app().innerHTML = `<p class="kicker">Convert</p><h1>Convert TCX files for Garmin Connect</h1>
    <p class="lead">Drop the TCX files you exported from Strava. Each one is converted straight away; download them one
      by one or all together as a zip, then import them in Garmin Connect.</p>
    <p class="privacy"><b>Your files stay on this device.</b> They are read and converted by JavaScript in this tab and
      are never uploaded${isStatic() ? ' (this site has no server)' : ' (the optional Python check sends them only to the app running on this computer)'}.</p>
    <label class="drop" id="drop" for="pick"><b>Drop .tcx files here</b><span class="small mute">or choose them (several at once is fine)</span>
      <input id="pick" type="file" accept=".tcx,${TCX_TYPE}" multiple></label>
    <div class="bar" style="margin-top:12px">
      <button class="alt" id="sample" type="button">Try the synthetic samples</button>
      <button id="all" type="button" hidden>Download all (.zip)</button>
      <button class="alt" id="pycheck" type="button" hidden>Check with the Python converter</button>
      <button class="alt" id="clear" type="button" hidden>Clear</button>
      <span class="small mute" id="count" aria-live="polite"></span></div>
    <details class="panel"><summary>Placeholder position for indoor workouts</summary>
      <p class="small mute">Garmin Connect expects a position on every trackpoint. Activities without GPS (Peloton, trainer
        rides) get this one; activities with recorded GPS keep their own route. Default: ${esc(info.default_place)}.</p>
      <div class="coords"><div><label for="lat">Latitude</label><input id="lat" inputmode="decimal" value="${info.default_lat}"></div>
        <div><label for="lng">Longitude</label><input id="lng" inputmode="decimal" value="${info.default_lng}"></div></div>
      <p class="small err" id="coord-err" aria-live="polite"></p></details>
    <div class="files" id="files"></div>
    ${isStatic() ? needsServer('Checking the output against the Python converter') : ''}`;

  const drop = $('#drop'), pick = $('#pick');
  pick.addEventListener('change', () => { addFiles([...pick.files], info); pick.value = ''; });
  ['dragenter', 'dragover'].forEach(ev => drop.addEventListener(ev, e => { e.preventDefault(); drop.classList.add('over'); }));
  ['dragleave', 'drop'].forEach(ev => drop.addEventListener(ev, () => drop.classList.remove('over')));
  drop.addEventListener('drop', e => { e.preventDefault(); addFiles([...e.dataTransfer.files], info); });
  const loadSamples = async () => {
    const enc = new TextEncoder();
    await addFiles((await api('/samples')).map(s => ({ name: s.name, bytes: enc.encode(s.text) })), info);
  };
  $('#sample').addEventListener('click', loadSamples);
  $('#clear').addEventListener('click', () => { entries = []; render(info); });
  $('#pycheck').addEventListener('click', () => pythonCheck(info));
  $('#all').addEventListener('click', () => {
    const good = entries.filter(e => e.out), names = uniqueNames(good.map(e => e.outName));
    download('garmin_tcx.zip', new Blob([makeZip(good.map((e, k) => ({ name: names[k], data: e.out })))], { type: 'application/zip' }));
  });
  $('#files').addEventListener('click', e => {
    const b = e.target.closest('[data-dl]');
    if (b) { const f = entries[+b.dataset.dl]; download(f.outName, f.out, TCX_TYPE); }
  });
  for (const id of ['#lat', '#lng']) $(id).addEventListener('change', () => {
    const c = coordsFrom(info);
    entries.forEach(e => convertOne(e, c));
    render(info);
  });
  render(info);
  if (query.sample) await loadSamples();
});
