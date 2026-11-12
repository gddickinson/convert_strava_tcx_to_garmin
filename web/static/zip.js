// Tiny ZIP writer (stored, no compression; UTF-8 names) for "download all". No library, runs in the browser and node.
const CRC_TABLE = (() => {
  const t = new Uint32Array(256);
  for (let n = 0; n < 256; n++) {
    let c = n;
    for (let k = 0; k < 8; k++) c = c & 1 ? 0xEDB88320 ^ (c >>> 1) : c >>> 1;
    t[n] = c >>> 0;
  }
  return t;
})();

export function crc32(bytes) {
  let c = 0xFFFFFFFF;
  for (let i = 0; i < bytes.length; i++) c = CRC_TABLE[(c ^ bytes[i]) & 0xFF] ^ (c >>> 8);
  return (c ^ 0xFFFFFFFF) >>> 0;
}

function dosTime(d) {
  return { time: (d.getHours() << 11) | (d.getMinutes() << 5) | (d.getSeconds() >> 1),
    date: ((Math.max(d.getFullYear(), 1980) - 1980) << 9) | ((d.getMonth() + 1) << 5) | d.getDate() };
}

// files: [{ name, data: Uint8Array | string }] -> Uint8Array holding the .zip
export function makeZip(files, when = new Date()) {
  const enc = new TextEncoder(), { time, date } = dosTime(when);
  const locals = [], centrals = [];
  let offset = 0;
  for (const f of files) {
    const name = enc.encode(f.name), data = typeof f.data === 'string' ? enc.encode(f.data) : f.data;
    const crc = crc32(data);
    const head = (sig, extra) => {
      const b = new DataView(new ArrayBuffer(extra ? 46 : 30));
      let p = 0;
      const u32 = v => { b.setUint32(p, v, true); p += 4; }, u16 = v => { b.setUint16(p, v, true); p += 2; };
      u32(sig); if (extra) u16(20);
      u16(20); u16(0x0800); u16(0); u16(time); u16(date); u32(crc); u32(data.length); u32(data.length);
      u16(name.length); u16(0);
      if (extra) { u16(0); u16(0); u16(0); u32(0); u32(offset); }
      return new Uint8Array(b.buffer);
    };
    const local = head(0x04034b50, false);
    locals.push(local, name, data);
    centrals.push(head(0x02014b50, true), name);
    offset += local.length + name.length + data.length;
  }
  const cdSize = centrals.reduce((a, b) => a + b.length, 0);
  const end = new DataView(new ArrayBuffer(22));
  end.setUint32(0, 0x06054b50, true); end.setUint16(8, files.length, true); end.setUint16(10, files.length, true);
  end.setUint32(12, cdSize, true); end.setUint32(16, offset, true);
  const parts = [...locals, ...centrals, new Uint8Array(end.buffer)];
  const out = new Uint8Array(parts.reduce((a, b) => a + b.length, 0));
  let p = 0;
  for (const x of parts) { out.set(x, p); p += x.length; }
  return out;
}

// Make names unique within one zip: a.tcx, a (2).tcx, ...
export function uniqueNames(names) {
  const seen = new Map();
  return names.map(n => {
    const k = (seen.get(n) || 0) + 1; seen.set(n, k);
    if (k === 1) return n;
    const dot = n.lastIndexOf('.');
    return dot > 0 ? `${n.slice(0, dot)} (${k})${n.slice(dot)}` : `${n} (${k})`;
  });
}
