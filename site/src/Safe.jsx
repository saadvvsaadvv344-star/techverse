import { useEffect, useRef, useState } from 'react';
import { DEMOS } from './demos/index.jsx';
import { EFFECTS } from './auric/registry.js';
import { Safe } from './Boundary.jsx';

/** /?selftest=1 - every demo and every effect at once, then a verdict for Auric's code check (headless Edge, phone size):
 *  no error, no console error, no sideways scrolling. Result: <pre id="selftest-result">{json}</pre> */
export function SelfTest() {
  if (new URLSearchParams(location.search).get('phone')) return <PhoneFrame />;
  return <SelfTestRun />;
}

/** Headless browsers won't make a window narrower than ~500px: the phone test runs the self-test in a real 375px frame. */
function PhoneFrame() {
  const [result, setResult] = useState(null);
  const ref = useRef(null);
  useEffect(() => {
    const t = setInterval(() => {
      const pre = ref.current && ref.current.contentDocument && ref.current.contentDocument.getElementById('selftest-result');
      if (pre && pre.textContent !== 'running') { setResult(pre.textContent); clearInterval(t); }
    }, 300);
    return () => clearInterval(t);
  }, []);
  return (
    <div>
      <iframe ref={ref} title="phone" src="/?selftest=1" style={{ width: 375, height: 812, border: 0 }} />
      <pre id="selftest-result">{result || 'running'}</pre>
    </div>
  );
}

function SelfTestRun() {
  const [result, setResult] = useState(null);
  useEffect(() => {
    const errors = (window.__tvErrors = window.__tvErrors || []);
    const orig = console.error;
    console.error = (...a) => { errors.push(a.map(String).join(' ').slice(0, 300)); orig(...a); };
    addEventListener('error', (e) => errors.push(`${e.message}`));
    const t = setTimeout(() => {
      window.scrollTo(0, document.body.scrollHeight);          // scroll effects run too (and really get a scroll event)
      dispatchEvent(new Event('scroll'));
      setTimeout(() => {
        // USE things, don't just load them: Auric's buttons must be visible and clickable, every button gets pressed
        const mine = [...document.querySelectorAll('button[class*="ax-"], a[class*="ax-"]')];
        const unusable = mine.filter((el) => {
          const s = getComputedStyle(el), r = el.getBoundingClientRect();
          return Number(s.opacity) < 0.1 || s.pointerEvents === 'none' || s.visibility === 'hidden' || !r.width || !r.height;
        }).map((el) => `${String(el.className).split(' ')[0]} is on screen but invisible or unclickable`);
        errors.push(...unusable);
        errors.push(...lowContrast());
        // the mouse moves over cards, buttons, headings and citations (hover effects run), then everything is clicked
        document.querySelectorAll('.card, .sec, .btn, h2, a.cite, .nav a').forEach((el) => {
          const r = el.getBoundingClientRect();
          try {
            for (const type of ['pointerover', 'pointerenter', 'pointermove', 'mouseover', 'mousemove', 'pointerleave']) {
              el.dispatchEvent(new PointerEvent(type, { bubbles: type !== 'pointerenter' && type !== 'pointerleave', clientX: r.left + r.width / 2, clientY: r.top + r.height / 2 }));
            }
          } catch (e) { errors.push(`hovering: ${e.message}`); }
        });
        [...mine, ...document.querySelectorAll('.demo button, [role="button"][class*="ax-"]')].forEach((b) => {
          try { b.click(); } catch (e) { errors.push(`clicking ${b.className || b.textContent}: ${e.message}`); }
        });
        setTimeout(() => {
          const wide = document.documentElement.scrollWidth > innerWidth + 1;
          // last: every effect is switched off, so a broken cleanup shows up as an error (checked just below)
          const before = errors.length;
          try { dispatchEvent(new Event('tv-unmount-effects')); } catch (e) { errors.push(`cleanup: ${e.message}`); }
          setTimeout(() => finish(wide, before), 600);
        }, 1500);
      }, 1200);
    }, 2500);
    const finish = (wide, before) => {
      if (errors.length > before) errors.splice(before, errors.length - before, ...errors.slice(before).map((e) => `when removed (cleanup): ${e}`));
      const offenders = wide ? [...document.querySelectorAll('body *')].filter((el) => el.getBoundingClientRect().right > innerWidth + 1)
        .slice(0, 5).map((el) => `${el.tagName.toLowerCase()}.${String(el.className).split(' ')[0]}`) : [];
      setResult({ ok: !errors.length && !wide, errors, wide, offenders, width: innerWidth,
        demos: Object.keys(DEMOS).length, effects: EFFECTS.length });
    };
    return () => clearTimeout(t);
  }, []);
  // a sample of every part of the site, so Auric's enhancers have real things to work on
  return (
    <div>
      <section className="hero">
        <h1>Everything in technology, <span className="grad">explained clearly.</span></h1>
        <p>Simple first, then deep.</p>
        <div className="hero-actions"><a href="#a" className="btn primary">Watch Auric write</a><a href="#b" className="btn">Surprise me</a></div>
      </section>
      <div className="sections">{['AI', 'Hardware'].map((s) => <a key={s} href={`#${s}`} className="sec"><span className="ic">🧠</span><b>{s}</b><small>A section.</small><em>12 pages</em></a>)}</div>
      <div className="cards">{[1, 2, 3, 4].map((i) => <a key={i} href={`#c${i}`} className="card"><small className="tag">🧠 AI</small><b>Card {i}</b><span>Text for the effects to work on.</span></a>)}</div>
      <article className="article">
        <h1>How a transistor works</h1>
        <p className="lead">A tiny switch that controls electricity.<sup><a href="#src-1" className="cite">1</a></sup></p>
        <section className="block"><h2>What it is</h2><p>A transistor is a switch.<sup><a href="#src-1" className="cite">1</a></sup> Billions sit on one chip.</p></section>
        <section className="block"><h2>How it works</h2><ol className="steps"><li>A small current arrives.</li><li>The gate opens.</li><li>A big current flows.</li></ol></section>
        <section className="block"><h2>At a glance</h2>
          <svg className="diagram" viewBox="0 0 300 80"><rect x="5" y="10" width="110" height="60" rx="10" fill="none" stroke="#4aa8ff" /><line x1="115" y1="40" x2="185" y2="40" stroke="#4aa8ff" /><rect x="185" y="10" width="110" height="60" rx="10" fill="none" stroke="#4aa8ff" /></svg>
        </section>
        <section className="block"><h2>Glossary</h2><dl className="glossary"><div><dt>Gate</dt><dd>The part that opens or closes the switch.</dd></div><div><dt>Chip</dt><dd>A piece of silicon with many transistors.</dd></div></dl></section>
        <p className="score">You got <b>3 / 3</b> — perfect! 🎉</p>
        <section className="block sources"><h2>Sources</h2><ol><li id="src-1"><a href="#x">Transistor (Wikipedia)</a></li></ol></section>
      </article>
      {Object.entries(DEMOS).map(([k, d]) => { const C = d.Component; return <section key={k} className="block"><h2>{d.name}</h2><Safe name={`demo ${k}`}><C /></Safe></section>; })}
      <pre id="selftest-result">{result ? JSON.stringify(result) : 'running'}</pre>
    </div>
  );
}

/** Text in Auric's elements must be readable: contrast of at least 3:1 against what's behind it. */
const rgba = (s) => (String(s).match(/[\d.]+/g) || []).map(Number);
function lum([r, g, b]) {
  const f = (c) => { const v = c / 255; return v <= 0.03928 ? v / 12.92 : ((v + 0.055) / 1.055) ** 2.4; };
  return 0.2126 * f(r) + 0.7152 * f(g) + 0.0722 * f(b);
}
function behind(el) {
  for (let e = el; e; e = e.parentElement) {
    const c = rgba(getComputedStyle(e).backgroundColor);
    if (c.length >= 3 && (c.length < 4 || c[3] > 0.5)) return c;
  }
  return rgba(getComputedStyle(document.body).backgroundColor);
}
function lowContrast() {
  const bad = [];
  document.querySelectorAll('[class*="ax-"]').forEach((el) => {
    const own = [...el.childNodes].some((n) => n.nodeType === 3 && n.textContent.trim());
    const s = getComputedStyle(el);
    if (!own || Number(s.opacity) < 0.1 || s.visibility === 'hidden') return;
    const a = lum(rgba(s.color)), b = lum(behind(el));
    const ratio = (Math.max(a, b) + 0.05) / (Math.min(a, b) + 0.05);
    if (ratio < 3) bad.push(`${String(el.className).split(' ')[0]}: text hard to read (contrast ${ratio.toFixed(1)}:1, needs 3:1)`);
  });
  return bad.slice(0, 3);
}
