// Python semantics the converter relies on, ported so the browser output is byte-identical to tcx_core.py:
// str.strip() whitespace, float(text), str(float), os.path.splitext and datetime.fromisoformat (CPython 3.12 rules)
// followed by astimezone(utc) and strftime('%Y-%m-%dT%H:%M:%S.000Z').

// Characters for which Python's str.isspace() is true (JS trim() differs: it strips U+FEFF, keeps U+001C-1F/U+0085).
const PY_SPACE = new Set([...'\t\n\v\f\r\x1c\x1d\x1e\x1f \x85\xa0     　']
  .concat(Array.from({ length: 11 }, (_, i) => String.fromCharCode(0x2000 + i))));

export function pyStrip(s) {
  let a = 0, b = s.length;
  while (a < b && PY_SPACE.has(s[a])) a++;
  while (b > a && PY_SPACE.has(s[b - 1])) b--;
  return s.slice(a, b);
}

// float(text): returns a number, or null where Python raises ValueError.
const FLOAT_RE = /^[+-]?(?:\d(?:_?\d)*(?:\.(?:\d(?:_?\d)*)?)?|\.\d(?:_?\d)*)(?:[eE][+-]?\d(?:_?\d)*)?$/;
const SPECIAL_RE = /^([+-]?)(inf|infinity|nan)$/i;
export function pyFloat(text) {
  const s = pyStrip(String(text));
  const sp = SPECIAL_RE.exec(s);
  if (sp) return sp[2].toLowerCase() === 'nan' ? NaN : (sp[1] === '-' ? -Infinity : Infinity);
  return FLOAT_RE.test(s) ? Number(s.replace(/_/g, '')) : null;
}

// str(x) / repr(x) for a Python float: shortest round-trip digits, scientific outside 1e-4 <= |x| < 1e16.
export function pyRepr(x) {
  if (Number.isNaN(x)) return 'nan';
  if (!Number.isFinite(x)) return x > 0 ? 'inf' : '-inf';
  if (x === 0) return Object.is(x, -0) ? '-0.0' : '0.0';
  const [mant, expS] = Math.abs(x).toExponential().split('e');
  const digits = mant.replace('.', ''), exp = +expS, sign = x < 0 ? '-' : '';
  if (exp >= -4 && exp < 16) {
    let s;
    if (exp < 0) s = '0.' + '0'.repeat(-exp - 1) + digits;
    else if (digits.length > exp + 1) s = digits.slice(0, exp + 1) + '.' + digits.slice(exp + 1);
    else s = digits + '0'.repeat(exp + 1 - digits.length) + '.0';
    return sign + s;
  }
  const m = digits.length > 1 ? digits[0] + '.' + digits.slice(1) : digits;
  return `${sign}${m}e${exp < 0 ? '-' : '+'}${String(Math.abs(exp)).padStart(2, '0')}`;
}

// os.path.splitext(name)[0] + '_garmin.tcx' (POSIX rules: leading dots do not start an extension).
export function garminOutputName(name) {
  const sep = name.lastIndexOf('/'), dot = name.lastIndexOf('.');
  let base = name;
  if (dot > sep) {
    for (let i = sep + 1; i < dot; i++) if (name[i] !== '.') { base = name.slice(0, dot); break; }
  }
  return base + '_garmin.tcx';
}

// --- datetime.fromisoformat (CPython 3.12 C implementation) ---------------------------------------------------------
const isDigit = c => c >= '0' && c <= '9';
const at = (s, i) => (i < s.length ? s[i] : '\0');   // C strings end in NUL

function digits(s, i, n) {   // parse_digits: exactly n ASCII digits at i -> [value, next] or null
  let v = 0;
  for (let k = 0; k < n; k++) { const c = at(s, i + k); if (!isDigit(c)) return null; v = v * 10 + (c.charCodeAt(0) - 48); }
  return [v, i + n];
}

// parse_hhmmss_micro over s[i, end): returns { rv, h, m, sec, us } (rv < 0 error, 1 = stopped before the end)
function hhmmss(s, i, end) {
  const vals = [0, 0, 0];
  let p = i, hasSep = true, frac = false;
  for (let k = 0; k < 3; k++) {
    const d = digits(s, p, 2);
    if (!d) return { rv: -3 };
    vals[k] = d[0]; p = d[1];
    const c = at(s, p++);
    if (k === 0) hasSep = c === ':';
    if (p >= end) return { rv: c !== '\0' ? 1 : 0, h: vals[0], m: vals[1], sec: vals[2], us: 0 };
    if (hasSep && c === ':') continue;
    if (c === '.' || c === ',') { frac = true; break; }
    if (!hasSep) p--; else return { rv: -4 };
  }
  const remain = end - p;
  const n = Math.min(remain, 6);
  if (n <= 0) return { rv: -3 };   // CPython reads out of bounds here; treat as invalid
  const d = digits(s, p, n);
  if (!d) return { rv: -3 };
  let us = d[0] * [100000, 10000, 1000, 100, 10, 1][n - 1];
  p = d[1];
  while (isDigit(at(s, p))) p++;
  return { rv: at(s, p) !== '\0' ? 1 : 0, h: vals[0], m: vals[1], sec: vals[2], us };
}

const DAYS = [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31];
const leap = y => (y % 4 === 0 && y % 100 !== 0) || y % 400 === 0;
const monthDays = (y, m) => (m === 2 && leap(y) ? 29 : DAYS[m - 1]);

// days since 1970-01-01 for a proleptic Gregorian date, and back (H. Hinnant's algorithms)
function daysFromCivil(y, m, d) {
  y -= m <= 2 ? 1 : 0;
  const era = Math.floor(y / 400), yoe = y - era * 400;
  const doy = Math.floor((153 * (m + (m > 2 ? -3 : 9)) + 2) / 5) + d - 1;
  return era * 146097 + yoe * 365 + Math.floor(yoe / 4) - Math.floor(yoe / 100) + doy - 719468;
}
function civilFromDays(z) {
  z += 719468;
  const era = Math.floor(z / 146097), doe = z - era * 146097;
  const yoe = Math.floor((doe - Math.floor(doe / 1460) + Math.floor(doe / 36524) - Math.floor(doe / 146096)) / 365);
  const doy = doe - (365 * yoe + Math.floor(yoe / 4) - Math.floor(yoe / 100));
  const mp = Math.floor((5 * doy + 2) / 153), d = doy - Math.floor((153 * mp + 2) / 5) + 1, m = mp + (mp < 10 ? 3 : -9);
  return [yoe + era * 400 + (m <= 2 ? 1 : 0), m, d];
}

// datetime.fromisoformat(s): { y, mo, d, h, mi, s, us, tz: null | [seconds, microseconds] } or null (ValueError).
// ISO week dates (YYYY-Www-D) are not ported (TCX never uses them): they return null here.
export function fromIsoFormat(s) {
  if (s.length === 7 || at(s, 4) === 'W' || (at(s, 4) === '-' && at(s, 5) === 'W')) return null;
  const sepAt = at(s, 4) === '-' ? 10 : 8;
  let p = 0;
  const yr = digits(s, p, 4); if (!yr) return null; p = yr[1];
  const useSep = at(s, p) === '-'; if (useSep) p++;
  const mo = digits(s, p, 2); if (!mo) return null; p = mo[1];
  if (useSep && at(s, p++) !== '-') return null;
  const dd = digits(s, p, 2); if (!dd) return null;
  const r = { y: yr[0], mo: mo[0], d: dd[0], h: 0, mi: 0, s: 0, us: 0, tz: null };
  if (sepAt < s.length) {
    const start = sepAt + 1, end = s.length;
    let tzPos = start;
    do { const c = at(s, tzPos); if (c === 'Z' || c === '+' || c === '-') break; } while (++tzPos < end);
    const t = hhmmss(s, start, tzPos);
    if (t.rv < 0) return null;
    Object.assign(r, { h: t.h, mi: t.m, s: t.sec, us: t.us });
    if (tzPos !== end) {
      if (s[tzPos] === 'Z') {
        if (tzPos + 1 !== end) return null;
        r.tz = [0, 0];
      } else {
        const sign = s[tzPos] === '-' ? -1 : 1;
        const z = hhmmss(s, tzPos + 1, end);
        if (z.rv !== 0) return null;
        const secs = sign * (z.h * 3600 + z.m * 60 + z.sec);
        r.tz = [secs, secs === 0 ? 0 : sign * z.us];   // CPython: a whole-second offset of 0 is UTC (microseconds ignored)
      }
    } else if (t.rv === 1) return null;
  }
  // datetime() and timezone() range checks
  if (r.y < 1 || r.mo < 1 || r.mo > 12 || r.d < 1 || r.d > monthDays(r.y, r.mo)) return null;
  if (r.h > 23 || r.mi > 59 || r.s > 59) return null;
  if (r.tz && Math.abs(r.tz[0] + r.tz[1] / 1e6) >= 86400) return null;
  return r;
}

const p2 = n => String(n).padStart(2, '0');

// tcx_core.format_garmin_time: ISO time -> 'YYYY-MM-DDTHH:MM:SS.000Z' in UTC; anything else (or null) unchanged.
export function formatGarminTime(text) {
  if (text == null) return text;
  const r = fromIsoFormat(text.replace(/Z/g, '+00:00'));
  if (!r) return text;
  let days = daysFromCivil(r.y, r.mo, r.d), secs = r.h * 3600 + r.mi * 60 + r.s, us = r.us;
  if (r.tz) {   // astimezone(utc): subtract the offset, carrying microseconds -> seconds -> days
    us -= r.tz[1]; secs -= r.tz[0];
    secs += Math.floor(us / 1e6); us -= Math.floor(us / 1e6) * 1e6;
    days += Math.floor(secs / 86400); secs -= Math.floor(secs / 86400) * 86400;
  }
  const [y, mo, d] = civilFromDays(days);
  if (y < 1 || y > 9999) return text;   // OverflowError in Python
  const h = Math.floor(secs / 3600), mi = Math.floor((secs % 3600) / 60), sec = secs % 60;
  return `${String(y).padStart(4, '0')}-${p2(mo)}-${p2(d)}T${p2(h)}:${p2(mi)}:${p2(sec)}.000Z`;
}
