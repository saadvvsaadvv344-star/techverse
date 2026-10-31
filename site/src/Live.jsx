import { useEffect, useLayoutEffect, useRef, useState } from 'react';
import { getLive, getShowcase } from './api.js';
import { Link } from './router.jsx';
import { sectionById } from './sections.js';

// Watch Auric work: the sources it reads pop in, the page it writes types itself out with Auric's cursor moving to
// the part it's on, and every sentence it checks is kept ✅ or cut ✂️ with the reason. Polls every 5 s.
const STEPS = [['research', 'Research'], ['write', 'Write'], ['check', 'Check'], ['publish', 'Publish'], ['code', 'Code the site']];
const typedOnce = new Set();

function Typed({ text, speed = 2 }) {
  const done = typedOnce.has(text);
  const [n, setN] = useState(done ? text.length : 0);
  useEffect(() => {
    if (typedOnce.has(text)) { setN(text.length); return undefined; }
    let i = 0;
    const t = setInterval(() => {
      i = Math.min(text.length, i + speed);
      setN(i);
      if (i >= text.length) { clearInterval(t); typedOnce.add(text); }
    }, 16);
    return () => clearInterval(t);
  }, [text, speed]);
  return <>{text.slice(0, n)}{n < text.length && <span className="caret" />}</>;
}

function Cursor({ box, focus, draft }) {
  const [pos, setPos] = useState({ x: 30, y: 30 });
  useLayoutEffect(() => {
    const root = box.current;
    if (!root) return;
    const els = root.querySelectorAll('[data-focus]');
    const el = [...els].find((e) => e.dataset.focus === focus) || els[els.length - 1];
    if (!el) return;
    const r = el.getBoundingClientRect(), b = root.getBoundingClientRect();
    setPos({ x: Math.min(r.right - b.left, b.width - 30) - 10, y: r.bottom - b.top - 6 });
  }, [box, focus, draft]);
  return (
    <svg className="auric-cursor" style={{ transform: `translate(${pos.x}px, ${pos.y}px)` }} width="26" height="34" viewBox="0 0 26 34" aria-hidden="true">
      <path d="M2 2 L2 26 L8.5 20 L13 31 L17.5 29 L13 18.5 L22 18.5 Z" fill="#fff" stroke="#4aa8ff" strokeWidth="2" strokeLinejoin="round" />
      <text x="0" y="0" />
    </svg>
  );
}

/** Drag the handle: left = before, right = after. */
function BeforeAfter({ s }) {
  const [p, setP] = useState(50);
  if (!s || !s.after) return null;
  return (
    <section className="live-col showcase">
      <h2>🎨 Auric’s latest design change: {s.name}</h2>
      <p className="muted">{s.about} <small>({new Date(s.time).toLocaleString()} · page {s.page})</small></p>
      {s.before ? (
        <div className="ba" style={{ '--p': `${p}%` }}>
          <img src={s.after} alt={`After: ${s.name}`} />
          <img src={s.before} alt="Before" className="ba-before" />
          <span className="ba-tag l">Before</span><span className="ba-tag r">After</span>
          <input type="range" min="0" max="100" value={p} onChange={(e) => setP(Number(e.target.value))} aria-label="Compare before and after" />
        </div>
      ) : <img src={s.after} alt={`After: ${s.name}`} className="ba-single" />}
    </section>
  );
}

const ago = (iso) => Math.round((Date.now() - new Date(iso).getTime()) / 1000);

export default function LivePage() {
  const [live, setLive] = useState(undefined);
  const [show, setShow] = useState(null);
  const [, tick] = useState(0);
  const box = useRef(null);
  const showTime = live && live.step === 'done' ? live.updated : '';
  useEffect(() => { getShowcase().then(setShow).catch(() => {}); }, [showTime]);
  useEffect(() => {
    let stop = false;
    const pull = () => getLive().then((l) => { if (!stop) setLive(l); }).catch(() => {});
    pull();
    const t = setInterval(pull, 5000), c = setInterval(() => tick((n) => n + 1), 1000);
    return () => { stop = true; clearInterval(t); clearInterval(c); };
  }, []);

  if (live === undefined) return <div className="loading" aria-busy="true"><span /><span /><span /></div>;
  if (!live) return <div className="empty"><h1>Live</h1><p>Auric hasn’t started its first cycle yet.</p></div>;

  const quiet = ['rest', 'wait', 'done'].includes(live.step);
  const stale = !quiet && ago(live.updated) > 180;
  const draft = live.draft || {};
  const sec = sectionById(live.section || '');
  const stepIdx = STEPS.findIndex(([k]) => k === live.step);
  const left = live.next ? Math.max(0, -ago(live.next)) : 0;

  return (
    <div className="live">
      <div className="live-head">
        <span className={`live-dot ${stale || quiet ? 'off' : ''}`}>{stale ? 'PAUSED' : quiet ? 'RESTING' : 'LIVE'}</span>
        <div>
          <h1>{stale ? 'Auric is paused' : live.subject ? <>Auric is {live.mode || 'working'}: <span className="grad">{live.subject}</span></> : 'Auric at work'}</h1>
          <p className="lead">
            {stale ? 'Auric is between two work sessions right now. Everything already published stays online; it continues where it left off.'
              : live.step === 'rest' ? `Resting. Next page in ${Math.floor(left / 60)} min ${left % 60} s.`
                : live.phase}
          </p>
        </div>
      </div>

      <ol className="live-steps">
        {STEPS.map(([k, label], i) => (
          <li key={k} className={i < stepIdx || live.step === 'done' ? 'past' : i === stepIdx ? 'now' : ''}>{label}</li>
        ))}
      </ol>
      {live.step === 'done' && live.slug && <p className="published">🎉 Published! <Link to={`/a/${live.slug}`} className="btn primary">Open the page</Link></p>}

      <div className="live-grid">
        <section className="live-col">
          <h2>📚 Reading</h2>
          {(live.sources || []).length ? (
            <ul className="src-pop">{live.sources.map((s, i) => <li key={s.title + i} style={{ animationDelay: `${i * 60}ms` }}><b>{s.site}</b><span>{s.title}</span></li>)}</ul>
          ) : <p className="muted">Sources appear here as Auric finds them.</p>}
        </section>

        {live.step === 'code' || (live.mode === 'coding the website' && live.code) ? (
          <section className="live-col page-col">
            <h2>💻 The code Auric is writing</h2>
            {live.code ? <pre className="code-live"><code><Typed text={live.code} speed={6} /></code></pre>
              : <p className="muted">Thinking about the code…</p>}
          </section>
        ) : (
        <section className="live-col page-col" style={{ '--sec': sec.color }}>
          <h2>✍️ The page being built</h2>
          <div className="draft" ref={box}>
            {draft.title ? (
              <>
                <h3 data-focus="title">{draft.title}</h3>
                {draft.summary && <p className="lead" data-focus="summary"><Typed text={draft.summary} /></p>}
                {(draft.body || []).map((b) => (
                  <div key={b.h} data-focus={b.h}>
                    <h4>{b.h}</h4>
                    {(b.p || []).map((p, i) => <p key={i}><Typed text={p} speed={3} /></p>)}
                  </div>
                ))}
                {live.focus && !(draft.body || []).some((b) => b.h === live.focus) && !['summary', 'extras', 'learn'].includes(live.focus) && (
                  <div data-focus={live.focus}><h4>{live.focus}</h4><p className="muted">writing…</p></div>
                )}
                {(draft.extras || []).length > 0 && <p className="chips-line" data-focus="extras">{draft.extras.map((x) => <span key={x}>✔ {x}</span>)}</p>}
                {live.focus === 'learn' && <p className="muted" data-focus="learn">Glossary and quiz…</p>}
                {!stale && !quiet && <Cursor box={box} focus={live.focus} draft={draft} />}
              </>
            ) : <p className="muted">{live.step === 'research' ? 'Reading the sources first…' : 'The page appears here as Auric writes it.'}</p>}
          </div>
        </section>
        )}

        <section className="live-col">
          <h2>🔎 Fact check</h2>
          {(live.checks || []).length ? (
            <ul className="checks">{[...live.checks].reverse().map((c, i) => (
              <li key={c.s + i} className={c.ok ? 'ok' : 'cut'}>
                <span>{c.ok ? '✅' : '✂️'}</span>
                <div><p>{c.s}</p><small>{c.ok ? `kept: ${c.why}` : `left out: ${c.why}`}</small></div>
              </li>
            ))}</ul>
          ) : <p className="muted">Every sentence is checked against the sources before anything is published.</p>}
        </section>
      </div>
      <BeforeAfter s={show} />
      <p className="muted small-note">{live.where ? `Working on ${live.where} · ` : ''}Updated {Math.max(0, ago(live.updated))} s ago · refreshes every 5 s.</p>
    </div>
  );
}
