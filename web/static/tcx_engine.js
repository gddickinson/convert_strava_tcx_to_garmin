// JS port of tcx_core.py (the Strava TCX -> Garmin Connect conversion). Same structure, function for function, so a
// change in the Python is easy to mirror; tcx_engine.test.mjs checks the output is byte-identical on tests/fixtures.
import { el, sub, setAttr, getAttr, iter, parseXml, indent, tostring } from './tcx_xml.js';
import { pyFloat, pyRepr, formatGarminTime } from './tcx_pyfmt.js';

export const DEFAULT_LAT = 30.2672;
export const DEFAULT_LNG = -97.7431;
export const DEFAULT_ALTITUDE = '192.60000610351562';
export const LX_FIELDS = ['AvgSpeed', 'MaxBikeCadence', 'AvgRunCadence', 'MaxRunCadence', 'Steps', 'AvgWatts', 'MaxWatts'];
const XSI = 'http://www.w3.org/2001/XMLSchema-instance';

export const localName = tag => tag.split('}').pop();
export const findChild = (e, name) => e.children.find(c => localName(c.tag) === name) ?? null;

// convert_tcx_bytes: TCX bytes (Uint8Array) or text -> Garmin-format XML text. Throws on invalid XML.
export function convertTcx(data, lat = DEFAULT_LAT, lng = DEFAULT_LNG) {
  const root = parseXml(data);
  const newRoot = el('TrainingCenterDatabase');
  const activities = sub(newRoot, 'Activities');
  let original = null;
  for (const e of iter(root)) if (e.tag.endsWith('Activities')) { original = e; break; }
  if (original) for (const a of original.children) activities.children.push(convertActivity(a, lat, lng));
  addAuthor(newRoot);
  return garminXmlString(newRoot);
}

function convertActivity(activity, lat, lng) {
  const a = el('Activity');
  setAttr(a, 'Sport', 'Other');
  const recorded = new Set([...iter(activity)].map(e => localName(e.tag)));
  const keep = { position: recorded.has('Position'), altitude: recorded.has('AltitudeMeters') };
  for (const child of activity.children) {
    const tag = localName(child.tag);
    if (tag === 'Id') sub(a, 'Id', formatGarminTime(child.text));
    else if (tag === 'Creator' || tag === 'Extensions') continue;
    else if (tag === 'Lap') a.children.push(convertLap(child, lat, lng, keep));
    else a.children.push(copyElement(child));
  }
  return a;
}

function convertLap(lap, lat, lng, keep) {
  const l = el('Lap');
  const start = getAttr(lap, 'StartTime');
  if (start) setAttr(l, 'StartTime', formatGarminTime(start));
  for (const child of lap.children) {
    const tag = localName(child.tag);
    if (tag === 'Track') l.children.push(convertTrack(child, lat, lng, keep));
    else if (tag === 'Extensions') sub(l, 'Extensions').children.push(convertLapExtensions(lap, child));
    else l.children.push(copyElement(child));
  }
  return l;
}

// lap_avg_speed: str(DistanceMeters / TotalTimeSeconds) when both parse as finite floats and time > 0, else null
export function lapAvgSpeed(lap) {
  const d = findChild(lap, 'DistanceMeters'), t = findChild(lap, 'TotalTimeSeconds');
  if (!d || !t || d.text == null || t.text == null) return null;
  const dv = pyFloat(d.text), tv = pyFloat(t.text);
  if (dv === null || tv === null || !Number.isFinite(dv) || !Number.isFinite(tv) || !(tv > 0)) return null;
  return pyRepr(dv / tv);
}

function convertLapExtensions(lap, ext) {
  const lxOut = el('ns3:LX'), lx = findChild(ext, 'LX');
  for (const name of LX_FIELDS) {
    const c = lx ? findChild(lx, name) : null;
    let text = c && c.text ? c.text : null;
    if (name === 'AvgSpeed' && text === null) text = lapAvgSpeed(lap);
    if (text !== null) sub(lxOut, 'ns3:' + name, text);
  }
  return lxOut;
}

function convertTrack(track, lat, lng, keep) {
  const t = el('Track');
  for (const tp of track.children) if (localName(tp.tag) === 'Trackpoint') t.children.push(convertTrackpoint(tp, lat, lng, keep));
  return t;
}

function convertTrackpoint(tp, lat, lng, keep) {
  const t = el('Trackpoint');
  const time = findChild(tp, 'Time');
  if (time) sub(t, 'Time', formatGarminTime(time.text));
  if (keep.position) {
    const pos = findChild(tp, 'Position');
    if (pos) t.children.push(copyElement(pos));
  } else {
    const pos = sub(t, 'Position');
    sub(pos, 'LatitudeDegrees', pyRepr(lat));
    sub(pos, 'LongitudeDegrees', pyRepr(lng));
  }
  if (keep.altitude) {
    const alt = findChild(tp, 'AltitudeMeters');
    if (alt) sub(t, 'AltitudeMeters', alt.text);
  } else sub(t, 'AltitudeMeters', DEFAULT_ALTITUDE);
  const dist = findChild(tp, 'DistanceMeters');
  if (dist) sub(t, 'DistanceMeters', dist.text);
  for (const name of ['HeartRateBpm', 'Cadence']) {
    const c = findChild(tp, name);
    if (c) t.children.push(copyElement(c));
  }
  const tpxOut = sub(sub(t, 'Extensions'), 'ns3:TPX');
  const ext = findChild(tp, 'Extensions');
  const tpx = ext ? findChild(ext, 'TPX') : null;
  if (tpx) {
    const speed = findChild(tpx, 'Speed'), watts = findChild(tpx, 'Watts');
    if (speed && speed.text) sub(tpxOut, 'ns3:Speed', speed.text);
    else if (watts && watts.text) {
      const w = pyFloat(watts.text);
      if (w !== null) sub(tpxOut, 'ns3:Speed', pyRepr(w / 50 > 0.1 ? w / 50 : 0.1));   // max(0.1, w / 50.0)
    }
    for (const name of ['RunCadence', 'Watts']) {
      const c = findChild(tpx, name);
      if (c && c.text) sub(tpxOut, 'ns3:' + name, c.text);
    }
  }
  return t;
}

function addAuthor(root) {
  const a = sub(root, 'Author');
  setAttr(a, `{${XSI}}type`, 'Application_t');
  sub(a, 'Name', 'Connect Api');
  const v = sub(sub(a, 'Build'), 'Version');
  [['VersionMajor', '25'], ['VersionMinor', '8'], ['BuildMajor', '0'], ['BuildMinor', '0']].forEach(([k, x]) => sub(v, k, x));
  sub(a, 'LangID', 'en');
  sub(a, 'PartNumber', '006-D2449-00');
}

function copyElement(e) {
  const c = el(localName(e.tag));
  for (const [k, v] of e.attrib) setAttr(c, k, v);
  if (e.text) c.text = e.text;
  if (e.tail) c.tail = e.tail;
  for (const ch of e.children) c.children.push(copyElement(ch));
  return c;
}

const HEADER = [
  '<?xml version="1.0" encoding="UTF-8"?>',
  '<TrainingCenterDatabase',
  '  xsi:schemaLocation="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2 http://www.garmin.com/xmlschemas/TrainingCenterDatabasev2.xsd"',
  '  xmlns:ns5="http://www.garmin.com/xmlschemas/ActivityGoals/v1"',
  '  xmlns:ns3="http://www.garmin.com/xmlschemas/ActivityExtension/v2"',
  '  xmlns:ns2="http://www.garmin.com/xmlschemas/UserProfile/v2"',
  '  xmlns="http://www.garmin.com/xmlschemas/TrainingCenterDatabase/v2"',
  '  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xmlns:ns4="http://www.garmin.com/xmlschemas/ProfileExtension/v1">',
];

function garminXmlString(root) {
  const lines = [...HEADER];
  indent(root, '  ', 2);
  for (const child of root.children) {
    const parts = tostring(child).split('\n');
    lines.push('  ' + parts[0], ...parts.slice(1, -1));
  }
  lines.push('</TrainingCenterDatabase>');
  return lines.join('\n');
}
