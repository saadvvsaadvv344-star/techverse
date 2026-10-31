import { useEffect, useRef, useState } from 'react';
import { AURIC_DEMOS } from '../auric/registry.js';
import { Safe } from '../Boundary.jsx';

/* ---------------------------------------------------------------- sorting visualizer */
function* bubble(a) {
  for (let i = 0; i < a.length; i++) for (let j = 0; j < a.length - i - 1; j++) {
    yield { cmp: [j, j + 1] };
    if (a[j] > a[j + 1]) { [a[j], a[j + 1]] = [a[j + 1], a[j]]; yield { swap: [j, j + 1] }; }
  }
}
function* insertion(a) {
  for (let i = 1; i < a.length; i++) for (let j = i; j > 0; j--) {
    yield { cmp: [j - 1, j] };
    if (a[j - 1] <= a[j]) break;
    [a[j - 1], a[j]] = [a[j], a[j - 1]]; yield { swap: [j - 1, j] };
  }
}
function* quick(a, lo = 0, hi = a.length - 1) {
  if (lo >= hi) return;
  const p = a[hi];
  let i = lo;
  for (let j = lo; j < hi; j++) {
    yield { cmp: [j, hi] };
    if (a[j] < p) { [a[i], a[j]] = [a[j], a[i]]; yield { swap: [i, j] }; i++; }
  }
  [a[i], a[hi]] = [a[hi], a[i]]; yield { swap: [i, hi] };
  yield* quick(a, lo, i - 1);
  yield* quick(a, i + 1, hi);
}
const ALGOS = { 'Bubble sort': bubble, 'Insertion sort': insertion, 'Quicksort': quick };
const shuffled = (n) => Array.from({ length: n }, () => 5 + Math.floor(Math.random() * 95));

function Sorting() {
  const [arr, setArr] = useState(() => shuffled(24));
  const [algo, setAlgo] = useState('Bubble sort');
  const [mark, setMark] = useState({});
  const [stats, setStats] = useState({ cmp: 0, swap: 0 });
  const [running, setRunning] = useState(false);
  const timer = useRef(null);
  useEffect(() => () => clearInterval(timer.current), []);
  function run() {
    const a = [...arr];
    const it = ALGOS[algo](a);
    let cmp = 0, swap = 0;
    setRunning(true);
    timer.current = setInterval(() => {
      const s = it.next();
      if (s.done) { clearInterval(timer.current); setRunning(false); setMark({}); return; }
      if (s.value.cmp) cmp++; else swap++;
      setMark(s.value); setStats({ cmp, swap }); setArr([...a]);
    }, 40);
  }
  return (
    <div className="demo">
      <div className="bars" aria-label="Bars to sort">
        {arr.map((v, i) => {
          const on = (mark.cmp || mark.swap || []).includes(i);
          return <i key={i} style={{ height: `${v}%` }} className={on ? (mark.swap ? 'swap' : 'cmp') : ''} />;
        })}
      </div>
      <div className="row">
        <select value={algo} onChange={(e) => setAlgo(e.target.value)} disabled={running} aria-label="Algorithm">
          {Object.keys(ALGOS).map((k) => <option key={k}>{k}</option>)}
        </select>
        <button onClick={run} disabled={running}>▶ Sort</button>
        <button onClick={() => { clearInterval(timer.current); setRunning(false); setMark({}); setArr(shuffled(24)); setStats({ cmp: 0, swap: 0 }); }}>🔀 Shuffle</button>
        <span className="muted">{stats.cmp} comparisons · {stats.swap} swaps</span>
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- binary converter */
function Binary() {
  const [n, setN] = useState(42);
  const bits = Array.from({ length: 8 }, (_, i) => (n >> (7 - i)) & 1);
  return (
    <div className="demo">
      <div className="bits">
        {bits.map((b, i) => (
          <button key={i} className={`bit ${b ? 'on' : ''}`} onClick={() => setN(n ^ (1 << (7 - i)))} aria-label={`Bit worth ${1 << (7 - i)}: ${b}`}>
            <b>{b}</b><small>{1 << (7 - i)}</small>
          </button>
        ))}
      </div>
      <div className="row">
        <label>Decimal <input type="number" min="0" max="255" value={n} onChange={(e) => setN(Math.max(0, Math.min(255, Number(e.target.value) || 0)))} /></label>
        <span>Hex <b>{n.toString(16).toUpperCase().padStart(2, '0')}</b></span>
        <span className="muted">= {bits.map((b, i) => (b ? 1 << (7 - i) : 0)).filter(Boolean).join(' + ') || '0'}</span>
      </div>
      <p className="muted">Tap a bit to switch it on or off: each one is worth twice the one on its right.</p>
    </div>
  );
}

/* ---------------------------------------------------------------- logic gates */
const GATES = {
  AND: (a, b) => a && b, OR: (a, b) => a || b, XOR: (a, b) => a !== b,
  NAND: (a, b) => !(a && b), NOR: (a, b) => !(a || b), NOT: (a) => !a,
};
function LogicGates() {
  const [g, setG] = useState('AND');
  const [a, setA] = useState(true);
  const [b, setB] = useState(false);
  const one = g === 'NOT';
  const out = GATES[g](a, b);
  const rows = one ? [[false], [true]] : [[false, false], [false, true], [true, false], [true, true]];
  return (
    <div className="demo">
      <div className="row">{Object.keys(GATES).map((k) => <button key={k} className={k === g ? 'on' : ''} onClick={() => setG(k)}>{k}</button>)}</div>
      <div className="gate">
        <div className="ins">
          <button className={`led ${a ? 'on' : ''}`} onClick={() => setA(!a)}>A = {a ? 1 : 0}</button>
          {!one && <button className={`led ${b ? 'on' : ''}`} onClick={() => setB(!b)}>B = {b ? 1 : 0}</button>}
        </div>
        <div className="chip">{g}</div>
        <div className={`led big ${out ? 'on' : ''}`}>OUT = {out ? 1 : 0}</div>
      </div>
      <table className="truth"><thead><tr><th>A</th>{!one && <th>B</th>}<th>OUT</th></tr></thead>
        <tbody>{rows.map((r, i) => <tr key={i} className={r[0] === a && (one || r[1] === b) ? 'now' : ''}>
          {r.map((v, j) => <td key={j}>{v ? 1 : 0}</td>)}<td>{GATES[g](...r) ? 1 : 0}</td></tr>)}</tbody></table>
    </div>
  );
}

/* ---------------------------------------------------------------- Caesar cipher */
function Caesar() {
  const [text, setText] = useState('Meet me at noon');
  const [k, setK] = useState(3);
  const shift = (s, n) => s.replace(/[a-z]/gi, (c) => {
    const base = c <= 'Z' ? 65 : 97;
    return String.fromCharCode(((c.charCodeAt(0) - base + n + 26 * 10) % 26) + base);
  });
  return (
    <div className="demo">
      <label className="block-label">Your message <input value={text} maxLength={120} onChange={(e) => setText(e.target.value)} /></label>
      <label className="block-label">Shift each letter by <b>{k}</b> <input type="range" min="1" max="25" value={k} onChange={(e) => setK(Number(e.target.value))} /></label>
      <p className="mono">🔒 {shift(text, k)}</p>
      <p className="muted">Only 25 possible shifts: a computer tries them all instantly. That’s why modern encryption uses keys with billions of billions of possibilities.</p>
    </div>
  );
}

/* ---------------------------------------------------------------- speed of data (latency) */
const PLACES = [['Across a city', 30], ['Paris → Madrid', 1050], ['London → New York', 5570], ['Casablanca → Tokyo', 11400], ['To a geostationary satellite and back', 71600]];
function Latency() {
  const [km, setKm] = useState(5570);
  const fiber = km / 200000 * 1000;          // light in glass fibre: about 200,000 km per second
  return (
    <div className="demo">
      <div className="row">{PLACES.map(([n, d]) => <button key={n} className={d === km ? 'on' : ''} onClick={() => setKm(d)}>{n}</button>)}</div>
      <label className="block-label">Distance: <b>{km.toLocaleString()} km</b>
        <input type="range" min="10" max="72000" step="10" value={km} onChange={(e) => setKm(Number(e.target.value))} /></label>
      <p>Light in a glass fibre covers about 200,000 km per second, so the trip takes at least <b>{fiber.toFixed(1)} ms</b> one way
        and <b>{(2 * fiber).toFixed(1)} ms</b> there and back, before any router or server adds its own delay.</p>
    </div>
  );
}

/* ---------------------------------------------------------------- pixels: mixing light */
function Pixels() {
  const [c, setC] = useState([255, 120, 40]);
  const hex = `#${c.map((v) => v.toString(16).padStart(2, '0')).join('').toUpperCase()}`;
  return (
    <div className="demo">
      <div className="pixel" style={{ background: hex }} aria-label={`Colour ${hex}`} />
      {['Red', 'Green', 'Blue'].map((n, i) => (
        <label key={n} className="block-label">{n} <b>{c[i]}</b>
          <input type="range" min="0" max="255" value={c[i]} onChange={(e) => setC(c.map((v, j) => (j === i ? Number(e.target.value) : v)))} /></label>
      ))}
      <p className="mono">{hex}</p>
      <p className="muted">A screen pixel is three tiny lights. Mixing their brightness (0–255 each) makes over 16 million colours.</p>
    </div>
  );
}

// + the demos Auric codes itself (src/auric/demos), each inside a safety wrapper
const auricDemos = Object.fromEntries(Object.entries(AURIC_DEMOS).map(([id, d]) => {
  const C = d.Component;
  return [id, { ...d, Component: (p) => <Safe name={`demo ${id}`}><C {...p} /></Safe> }];
}));

export const DEMOS = {
  ...auricDemos,
  sorting: { name: 'Sorting visualizer', about: 'Watch three sorting algorithms put bars in order, and count their steps.', Component: Sorting },
  binary: { name: 'Binary converter', about: 'Switch bits on and off and see the number they make.', Component: Binary },
  'logic-gates': { name: 'Logic-gate simulator', about: 'AND, OR, XOR, NOT…: the tiny decisions every chip is made of.', Component: LogicGates },
  caesar: { name: 'Caesar cipher', about: 'The oldest secret code, and why it is easy to break.', Component: Caesar },
  latency: { name: 'Speed of data', about: 'How long light takes to carry your data across the world.', Component: Latency },
  pixels: { name: 'Pixel colour mixer', about: 'Mix red, green and blue light like a screen does.', Component: Pixels },
};
