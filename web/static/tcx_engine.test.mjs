// Node test: the JS port must give byte-identical output to the Python converter (tcx_core.py) on the synthetic
// samples, and the same results for the Python behaviours it re-implements. Reference files come from
// scripts/make_tcx_fixture.py. Run: node web/static/tcx_engine.test.mjs
import { readFileSync, readdirSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { join, dirname } from 'node:path';
import assert from 'node:assert/strict';
import { convertTcx, lapAvgSpeed } from './tcx_engine.js';
import { formatGarminTime, pyFloat, pyRepr, garminOutputName } from './tcx_pyfmt.js';
import { summarize, routeSvg } from './tcx_summary.js';
import { crc32, makeZip, uniqueNames } from './zip.js';

const FIX = join(dirname(fileURLToPath(import.meta.url)), '..', '..', 'tests', 'fixtures');
const values = JSON.parse(readFileSync(join(FIX, 'tcx_values.json'), 'utf8'));
let n = 0;
const check = (name, fn) => { try { fn(); n++; } catch (e) { console.error('FAIL', name); throw e; } };

// 1. whole files, byte for byte
const inputs = readdirSync(FIX).filter(f => f.endsWith('.tcx')).sort();
assert.ok(inputs.length >= 3, 'samples missing');
for (const f of inputs) {
  const data = new Uint8Array(readFileSync(join(FIX, f)));
  check(f, () => assert.ok(Buffer.from(new TextEncoder().encode(convertTcx(data))).equals(readFileSync(join(FIX, 'expected', f))), `${f} differs from Python`));
  if (values.custom.files.includes(f.replace('.tcx', ''))) {
    const exp = readFileSync(join(FIX, 'expected', f.replace('.tcx', '.custom.tcx')), 'utf8');
    check(f + ' custom', () => assert.equal(convertTcx(data, values.custom.lat, values.custom.lng), exp));
  }
}

// 2. Python behaviours re-implemented in JS
for (const [t, want] of values.times) check('time ' + t, () => assert.equal(formatGarminTime(t), want, t));
for (const [t, want] of values.floats) check('float ' + t, () => {
  const v = pyFloat(t);
  assert.equal(v === null ? null : pyRepr(v), want, JSON.stringify(t));
});
for (const [x, want] of values.reprs) check('repr ' + x, () => assert.equal(pyRepr(x), want));
for (const [t, want] of values.speeds) check('speed ' + t, () => {
  const w = pyFloat(t);
  assert.equal(w === null ? null : pyRepr(w / 50 > 0.1 ? w / 50 : 0.1), want, t);
});
for (const [name, want] of values.names) check('name ' + name, () => assert.equal(garminOutputName(name), want));
for (const [d, t, want] of values.lap_speeds) check(`lap speed ${d}/${t}`, () => {
  const lap = { children: [{ tag: 'TotalTimeSeconds', text: t, children: [] }, { tag: 'DistanceMeters', text: d, children: [] }] };
  assert.equal(lapAvgSpeed(lap), want);
});
check('time null', () => assert.equal(formatGarminTime(null), null));

// 3. preview summary, same numbers as the Python in make_tcx_fixture.py
for (const [f, want] of Object.entries(values.summaries)) check('summary ' + f, () => {
  const got = summarize(new Uint8Array(readFileSync(join(FIX, f))));
  for (const [k, v] of Object.entries(want)) {
    if (typeof v === 'number') assert.ok(Math.abs(got[k] - v) <= 1e-9 * Math.max(1, Math.abs(v)), `${f} ${k}: ${got[k]} vs ${v}`);
    else assert.deepEqual(got[k], v, `${f} ${k}`);
  }
  assert.equal(got.route.length, want.gps_points);
});
check('route svg', () => {
  const s = summarize(new Uint8Array(readFileSync(join(FIX, 'outdoor_run.tcx'))));
  assert.match(routeSvg(s.route), /<polyline points="[\d., ]+"/);
  assert.equal(routeSvg([]), null);
});

// 4. invalid input raises like ET.ParseError
for (const bad of ['not xml at all <<<<', '<a><b></a>', '<a>&nope;</a>', '<a/><b/>', '<p:a/>', '', '<a x="1" x="2"/>'])
  check('invalid ' + bad, () => assert.throws(() => convertTcx(bad), /Invalid TCX file/));
check('no activities', () => assert.match(convertTcx('<a/>'), /<Activities \/>/));

// 5. zip writer
check('crc32', () => {
  assert.equal(crc32(new TextEncoder().encode('hello')), 0x3610a686);
  assert.equal(crc32(new TextEncoder().encode('The quick brown fox jumps over the lazy dog')), 0x414fa339);
});
check('zip layout', () => {
  const z = makeZip([{ name: 'a.tcx', data: 'abc' }, { name: 'é.tcx', data: new Uint8Array([1, 2]) }]);
  const dv = new DataView(z.buffer);
  assert.equal(dv.getUint32(0, true), 0x04034b50);
  const eocd = z.length - 22;
  assert.equal(dv.getUint32(eocd, true), 0x06054b50);
  assert.equal(dv.getUint16(eocd + 10, true), 2);
  assert.equal(dv.getUint32(dv.getUint32(eocd + 16, true), true), 0x02014b50);
});
check('unique names', () => assert.deepEqual(uniqueNames(['a.tcx', 'a.tcx', 'b', 'b']), ['a.tcx', 'a (2).tcx', 'b', 'b (2)']));

console.log(`ok ${n} checks (${inputs.length} sample files byte-identical to Python)`);
