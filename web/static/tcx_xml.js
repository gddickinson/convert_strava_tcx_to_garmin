// Minimal XML layer with xml.etree.ElementTree semantics, so the JS converter matches tcx_core.py byte for byte:
// parse (expat + TreeBuilder: namespaces as '{uri}local', comments/PIs dropped, text/tail), ET.indent and
// ET.tostring (namespace prefixes, escaping, ' />' for empty elements). Elements: { tag, attrib: [[k, v]], text,
// tail, children }.
import { pyStrip } from './tcx_pyfmt.js';

export const el = (tag, text = null) => ({ tag, attrib: [], text, tail: null, children: [] });
export const sub = (parent, tag, text = null) => { const e = el(tag, text); parent.children.push(e); return e; };
export function setAttr(e, k, v) {
  const i = e.attrib.findIndex(a => a[0] === k);
  if (i >= 0) e.attrib[i][1] = v; else e.attrib.push([k, v]);
}
export const getAttr = (e, k) => (e.attrib.find(a => a[0] === k) || [])[1] ?? null;
export function* iter(e) { yield e; for (const c of e.children) yield* iter(c); }

// --- bytes -> text (expat honours the BOM and the declared encoding) ----------------------------------------------
export function decodeXml(bytes) {
  if (typeof bytes === 'string') return bytes;
  const b = bytes;
  let label = 'utf-8';
  if (b[0] === 0xFF && b[1] === 0xFE) label = 'utf-16le';
  else if (b[0] === 0xFE && b[1] === 0xFF) label = 'utf-16be';
  else if (!(b[0] === 0xEF && b[1] === 0xBB && b[2] === 0xBF)) {
    const head = String.fromCharCode(...b.subarray(0, 200));
    const m = /^<\?xml[^>]*?encoding\s*=\s*["']([A-Za-z0-9._-]+)["']/.exec(head);
    if (m) label = m[1].toLowerCase();
  }
  try { return new TextDecoder(label, { fatal: true }).decode(b); }   // strips a BOM
  catch (e) { throw new Error(`Invalid TCX file: cannot decode as ${label}`); }
}

// --- parser ---------------------------------------------------------------------------------------------------------
const XML_NS = 'http://www.w3.org/XML/1998/namespace';
const ENT = { amp: '&', lt: '<', gt: '>', quot: '"', apos: "'" };
const NAME = /[A-Za-z_:À-￯][-\w.:·À-￯]*/y;
const XML_DECL = /^<\?xml\s+version\s*=\s*(["'])1\.[0-9]+\1(\s+encoding\s*=\s*(["'])[A-Za-z][A-Za-z0-9._-]*\3)?(\s+standalone\s*=\s*(["'])(yes|no)\5)?\s*\?>$/;
const NOT_WS = /[^ \t\n]/;   // XML whitespace outside the root (narrower than str.isspace)
const BAD_CHAR = /[\x00-\x08\x0B\x0C\x0E-\x1F￾￿]/;

function fail(msg, s, i) {
  const line = s.slice(0, i).split('\n').length;
  throw new Error(`Invalid TCX file: ${msg} (line ${line})`);
}

function decodeEntities(raw, s, pos) {
  return raw.replace(/&([^;&]*);|&/g, (m, name) => {
    if (name === undefined) fail('not well-formed (invalid token)', s, pos);
    if (name[0] === '#') {
      const code = name[1] === 'x' ? parseInt(name.slice(2), 16) : parseInt(name.slice(1), 10);
      const ok = /^#(x[0-9a-fA-F]+|[0-9]+)$/.test(name) && code <= 0x10FFFF &&
        (code === 9 || code === 10 || code === 13 || (code >= 0x20 && code <= 0xD7FF) ||
         (code >= 0xE000 && code <= 0xFFFD) || code >= 0x10000);
      if (!ok) fail('reference to invalid character number', s, pos);
      return String.fromCodePoint(code);
    }
    if (!(name in ENT)) fail('undefined entity', s, pos);
    return ENT[name];
  });
}

// ET.fromstring(bytes): returns the root element; throws Error('Invalid TCX file: ...') where Python raises ParseError.
export function parseXml(input) {
  const s = decodeXml(input).replace(/\r\n?/g, '\n');
  if (BAD_CHAR.test(s)) fail('not well-formed (invalid token)', s, s.search(BAD_CHAR));
  let i = 0, root = null, data = [];
  const stack = [];          // open elements: { e, qname, ns }
  let last = null;           // TreeBuilder: element whose text (open) or tail (closed) receives data
  let lastIsEnd = false;
  const flush = () => {
    if (!data.length) return;
    const t = data.join(''); data = [];
    if (!last) { if (NOT_WS.test(t)) fail(root ? 'junk after document element' : 'syntax error', s, i); return; }
    if (lastIsEnd) last.tail = t; else last.text = t;
  };
  const resolve = (qname, nsmap, isAttr) => {
    const c = qname.indexOf(':');
    if (c < 0) return isAttr || !nsmap[''] ? qname : `{${nsmap['']}}${qname}`;
    const prefix = qname.slice(0, c), local = qname.slice(c + 1);
    const uri = prefix === 'xml' ? XML_NS : nsmap[prefix];
    if (!uri) fail('unbound prefix', s, i);
    return `{${uri}}${local}`;
  };
  while (i < s.length) {
    const lt = s.indexOf('<', i);
    if (lt < 0) {
      if (!stack.length && NOT_WS.test(s.slice(i))) fail('junk after document element', s, i);
      data.push(decodeEntities(s.slice(i), s, i)); i = s.length; break;
    }
    if (lt > i) {
      const raw = s.slice(i, lt);
      if (!stack.length && NOT_WS.test(raw)) fail(root ? 'junk after document element' : 'syntax error', s, i);
      data.push(decodeEntities(raw, s, i));
    }
    i = lt;
    if (s.startsWith('<!--', i)) {
      const e = s.indexOf('-->', i + 4); if (e < 0) fail('unclosed token', s, i); i = e + 3;
    } else if (s.startsWith('<?', i)) {
      const e = s.indexOf('?>', i + 2); if (e < 0) fail('unclosed token', s, i);
      if (/^<\?xml(\s|\?)/.test(s.slice(i, i + 6))) {   // the XML declaration: only at the start, well-formed
        const off = s[0] === '\ufeff' ? 1 : 0;
        if (i !== off) fail('XML or text declaration not at start of entity', s, i);
        if (!XML_DECL.test(s.slice(i, e + 2))) fail('XML declaration not well-formed', s, i);
      }
      i = e + 2;
    } else if (s.startsWith('<![CDATA[', i)) {
      if (!stack.length) fail('syntax error', s, i);
      const e = s.indexOf(']]>', i + 9); if (e < 0) fail('unclosed CDATA section', s, i);
      data.push(s.slice(i + 9, e)); i = e + 3;
    } else if (s.startsWith('<!DOCTYPE', i)) {
      let depth = 0, j = i + 9;
      for (; j < s.length; j++) { const c = s[j]; if (c === '[') depth++; else if (c === ']') depth--; else if (c === '>' && depth <= 0) break; }
      i = j + 1;
    } else if (s[i + 1] === '/') {
      NAME.lastIndex = i + 2; const m = NAME.exec(s);
      const top = stack.pop();
      if (!m || !top || m[0] !== top.qname) fail('mismatched tag', s, i);
      const gt = s.indexOf('>', NAME.lastIndex);
      if (gt < 0 || s.slice(NAME.lastIndex, gt).trim()) fail('not well-formed (invalid token)', s, i);
      flush(); last = top.e; lastIsEnd = true; i = gt + 1;
    } else {
      if (root && !stack.length) fail('junk after document element', s, i);
      NAME.lastIndex = i + 1; const m = NAME.exec(s);
      if (!m) fail('not well-formed (invalid token)', s, i);
      let j = NAME.lastIndex; const raw = [];
      for (;;) {
        const ws = /\s*/y; ws.lastIndex = j; ws.exec(s); const hadSpace = ws.lastIndex > j; j = ws.lastIndex;
        if (s[j] === '>' || s.startsWith('/>', j)) break;
        NAME.lastIndex = j; const an = NAME.exec(s);
        if (!an || !hadSpace) fail('not well-formed (invalid token)', s, j);
        const eq = /\s*=\s*(["'])/y; eq.lastIndex = NAME.lastIndex; const q = eq.exec(s);
        if (!q) fail('not well-formed (invalid token)', s, j);
        const end = s.indexOf(q[1], eq.lastIndex);
        if (end < 0) fail('unclosed token', s, j);
        const val = s.slice(eq.lastIndex, end);
        if (val.includes('<')) fail('not well-formed (invalid token)', s, j);
        raw.push([an[0], decodeEntities(val.replace(/[\t\n]/g, ' '), s, j)]);
        j = end + 1;
      }
      const parentNs = stack.length ? stack[stack.length - 1].ns : { '': '' };
      const ns = { ...parentNs };
      for (const [k, v] of raw) {
        if (k === 'xmlns') ns[''] = v; else if (k.startsWith('xmlns:')) ns[k.slice(6)] = v;
      }
      const e = el(resolve(m[0], ns, false));
      for (const [k, v] of raw) {
        if (k === 'xmlns' || k.startsWith('xmlns:')) continue;
        const key = resolve(k, ns, true);
        if (e.attrib.some(a => a[0] === key)) fail('duplicate attribute', s, j);
        e.attrib.push([key, v]);
      }
      flush();
      if (stack.length) stack[stack.length - 1].e.children.push(e); else root = e;
      const selfClose = s[j] === '/';
      i = j + (selfClose ? 2 : 1);
      if (selfClose) { last = e; lastIsEnd = true; } else { stack.push({ e, qname: m[0], ns }); last = e; lastIsEnd = false; }
    }
  }
  if (stack.length) fail('no element found', s, i);
  if (!root) fail('no element found', s, i);
  flush();
  return root;
}

// --- ET.indent ------------------------------------------------------------------------------------------------------
export function indent(tree, space = '  ', level = 0) {
  if (!tree.children.length) return;
  const ind = ['\n' + space.repeat(level)];
  const rec = (elem, lvl) => {
    const childLvl = lvl + 1;
    if (ind[childLvl] === undefined) ind.push(ind[lvl] + space);
    const childInd = ind[childLvl];
    if (!elem.text || !pyStrip(elem.text)) elem.text = childInd;
    let child;
    for (child of elem.children) {
      if (child.children.length) rec(child, childLvl);
      if (!child.tail || !pyStrip(child.tail)) child.tail = childInd;
    }
    if (!pyStrip(child.tail)) child.tail = ind[lvl];
  };
  rec(tree, 0);
}

// --- ET.tostring(elem, encoding='unicode') --------------------------------------------------------------------------
const NS_MAP = {
  'http://www.w3.org/XML/1998/namespace': 'xml', 'http://www.w3.org/1999/xhtml': 'html',
  'http://www.w3.org/1999/02/22-rdf-syntax-ns#': 'rdf', 'http://schemas.xmlsoap.org/wsdl/': 'wsdl',
  'http://www.w3.org/2001/XMLSchema': 'xs', 'http://www.w3.org/2001/XMLSchema-instance': 'xsi',
  'http://purl.org/dc/elements/1.1/': 'dc',
};
const escCdata = t => t.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
const escAttr = t => escCdata(t).replace(/"/g, '&quot;').replace(/\r/g, '&#13;').replace(/\n/g, '&#10;').replace(/\t/g, '&#09;');

export function tostring(root) {
  const namespaces = new Map(), qnames = new Map();
  const add = q => {
    if (qnames.has(q)) return;
    if (q[0] !== '{') { qnames.set(q, q); return; }
    const k = q.lastIndexOf('}'), uri = q.slice(1, k), local = q.slice(k + 1);
    let prefix = namespaces.get(uri);
    if (prefix === undefined) {
      prefix = NS_MAP[uri] ?? `ns${namespaces.size}`;
      if (prefix !== 'xml') namespaces.set(uri, prefix);
    }
    qnames.set(q, prefix ? `${prefix}:${local}` : local);
  };
  for (const e of iter(root)) { add(e.tag); for (const [k] of e.attrib) add(k); }
  const out = [];
  const ser = (e, decl) => {
    const tag = qnames.get(e.tag);
    out.push('<' + tag);
    if (decl) {
      [...namespaces].sort((a, b) => (a[1] < b[1] ? -1 : a[1] > b[1] ? 1 : 0))
        .forEach(([uri, p]) => out.push(` xmlns${p ? ':' + p : ''}="${escAttr(uri)}"`));
    }
    for (const [k, v] of e.attrib) out.push(` ${qnames.get(k)}="${escAttr(v)}"`);
    if (e.text || e.children.length) {
      out.push('>');
      if (e.text) out.push(escCdata(e.text));
      for (const c of e.children) ser(c, false);
      out.push(`</${tag}>`);
    } else out.push(' />');
    if (e.tail) out.push(escCdata(e.tail));
  };
  ser(root, true);
  return out.join('');
}
