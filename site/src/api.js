// TechVerse reads Firestore through its REST API (no SDK: the site stays small and fast). Everything is public data;
// visitors can only add a +1 view and a search that found nothing (see firestore.rules).
const DB = 'https://firestore.googleapis.com/v1/projects/techverse-saad/databases/(default)/documents';

function dec(v) {
  const [kind, x] = Object.entries(v)[0];
  if (kind === 'nullValue') return null;
  if (kind === 'integerValue') return Number(x);
  if (kind === 'doubleValue') return Number(x);
  if (kind === 'arrayValue') return (x.values || []).map(dec);
  if (kind === 'mapValue') return decFields(x.fields || {});
  return x;
}
const decFields = (f) => Object.fromEntries(Object.entries(f || {}).map(([k, v]) => [k, dec(v)]));

const cache = new Map();
async function getDoc(path) {
  if (cache.has(path)) return cache.get(path);
  const p = fetch(`${DB}/${path}`).then(async (r) => {
    if (r.status === 404) return null;
    if (!r.ok) throw new Error(`HTTP ${r.status}`);
    return decFields((await r.json()).fields);
  });
  cache.set(path, p);
  p.catch(() => cache.delete(path));
  return p;
}
async function listDocs(path) {
  const r = await fetch(`${DB}/${path}`);
  if (!r.ok) return [];
  return ((await r.json()).documents || []).map((d) => ({ id: d.name.split('/').pop(), ...decFields(d.fields) }));
}

/** meta/index: { items: [{ slug, title, section, summary, updated, status, dates, terms, quiz }], updated } */
export const getIndex = () => getDoc('meta/index').then((d) => d || { items: [] });
/** meta/live: what Auric is doing right now (always fresh, never cached). */
export async function getLive() {
  const r = await fetch(`${DB}/meta/live`, { cache: 'no-store' });
  if (!r.ok) return null;
  return decFields((await r.json()).fields);
}
/** meta/showcase: Auric's latest design change, with before / after screenshots. */
export async function getShowcase() {
  const r = await fetch(`${DB}/meta/showcase`, { cache: 'no-store' });
  if (!r.ok) return null;
  return decFields((await r.json()).fields);
}
export const getArticle = (slug) => getDoc(`articles/${encodeURIComponent(slug)}`);
export const getHistory = () => listDocs('history?pageSize=40&orderBy=time%20desc');
export const getTopViews = () => listDocs('views?pageSize=8&orderBy=n%20desc');

export function countView(slug) {
  const key = `tv-seen-${slug}`;
  try { if (sessionStorage.getItem(key)) return; sessionStorage.setItem(key, '1'); } catch { /* fine */ }
  fetch(`${DB}:commit`, {
    method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ writes: [{ transform: {
      document: `projects/techverse-saad/databases/(default)/documents/views/${encodeURIComponent(slug)}`,
      fieldTransforms: [{ fieldPath: 'n', increment: { integerValue: '1' } }] } }] }),
  }).catch(() => {});
}

export function logMiss(q) {
  const text = String(q).trim().toLowerCase().slice(0, 80);
  if (text.length < 2) return;
  fetch(`${DB}/misses`, { method: 'POST', headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ fields: { q: { stringValue: text } } }) }).catch(() => {});
}
