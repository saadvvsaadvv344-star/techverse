import { useEffect, useMemo, useState } from 'react';
import { Link, go } from './router.jsx';
import { SECTIONS, sectionById } from './sections.js';
import { getHistory, getTopViews, getArticle, logMiss } from './api.js';
import { DEMOS } from './demos/index.jsx';
import Quiz from './Quiz.jsx';

const allSections = (index) => [...SECTIONS, ...((index && index.sections) || []).filter((s) => !SECTIONS.some((x) => x.id === s.id))];
const Loading = () => <div className="loading" aria-busy="true"><span /><span /><span /></div>;

function Card({ it, index }) {
  const s = sectionById(it.section, (index && index.sections) || []);
  return (
    <Link to={`/a/${it.slug}`} className="card" style={{ '--sec': s.color }}>
      <small className="tag">{s.icon} {s.name}</small>
      <b>{it.title}</b>
      <span>{it.summary}</span>
    </Link>
  );
}

function Empty({ text }) {
  return <div className="empty"><div className="orbit"><i /></div><p>{text}</p></div>;
}

/* ---------------------------------------------------------------- home */
export function Home({ index }) {
  const [top, setTop] = useState([]);
  useEffect(() => { getTopViews().then(setTop).catch(() => {}); }, []);
  const items = (index && index.items) || [];
  const latest = [...items].sort((a, b) => String(b.updated).localeCompare(String(a.updated))).slice(0, 6);
  const count = (id) => items.filter((i) => i.section === id).length;
  const popular = top.map((v) => items.find((i) => i.slug === v.id)).filter(Boolean).slice(0, 4);
  const random = items.length ? items[Math.floor(Math.random() * items.length)] : null;
  return (
    <div className="home">
      <section className="hero">
        <h1>Everything in technology, <span className="grad">explained clearly.</span></h1>
        <p>Simple first, then deep. Every fact has a source, every page is checked, and new pages appear every day.</p>
        <div className="hero-actions">
          <Link to="/live" className="btn primary">🔴 Watch Auric write</Link>
          {random && <Link to={`/a/${random.slug}`} className="btn">🎲 Surprise me</Link>}
          <Link to="/map" className="btn">🗺️ Explore the map</Link>
          <span className="muted">{items.length} pages written by Auric</span>
        </div>
      </section>

      <h2 className="h">Topics</h2>
      <div className="sections">
        {allSections(index).map((s) => (
          <Link key={s.id} to={`/s/${s.id}`} className="sec" style={{ '--sec': s.color }}>
            <span className="ic">{s.icon}</span><b>{s.name}</b><small>{s.blurb}</small><em>{count(s.id)} pages</em>
          </Link>
        ))}
      </div>

      {index === null ? <Loading /> : latest.length ? (
        <>
          <h2 className="h">Newest pages</h2>
          <div className="cards">{latest.map((it) => <Card key={it.slug} it={it} index={index} />)}</div>
        </>
      ) : <Empty text="Auric is researching and writing the first pages right now. Come back soon!" />}

      {popular.length > 0 && (
        <>
          <h2 className="h">Most read</h2>
          <div className="cards">{popular.map((it) => <Card key={it.slug} it={it} index={index} />)}</div>
        </>
      )}

      <h2 className="h">Try a live demo</h2>
      <div className="cards small">
        {Object.entries(DEMOS).slice(0, 3).map(([id, d]) => <Link key={id} to={`/demos/${id}`} className="card"><b>{d.name}</b><span>{d.about}</span></Link>)}
      </div>
    </div>
  );
}

/* ---------------------------------------------------------------- one section */
export function SectionPage({ id, index }) {
  const s = sectionById(id, (index && index.sections) || []);
  const items = ((index && index.items) || []).filter((i) => i.section === id).sort((a, b) => a.title.localeCompare(b.title));
  return (
    <div style={{ '--sec': s.color }}>
      <nav className="crumbs"><Link to="/">Home</Link> › {s.name}</nav>
      <h1 className="sec-title"><span>{s.icon}</span> {s.name}</h1>
      <p className="lead">{s.blurb}</p>
      {index === null ? <Loading /> : items.length
        ? <div className="cards">{items.map((it) => <Card key={it.slug} it={it} index={index} />)}</div>
        : <Empty text="No pages here yet: Auric picks sections with few pages first, so this one is coming soon." />}
    </div>
  );
}

/* ---------------------------------------------------------------- search */
const norm = (s) => String(s || '').toLowerCase().normalize('NFD').replace(/[̀-ͯ]/g, '');
export function SearchPage({ q, index }) {
  const hits = useMemo(() => {
    const words = norm(q).split(/\W+/).filter((w) => w.length > 1);
    if (!words.length || !index) return [];
    return index.items.map((it) => {
      const title = norm(it.title), body = norm(`${it.summary} ${(it.terms || []).join(' ')}`);
      const score = words.reduce((s, w) => s + (title.includes(w) ? 3 : 0) + (body.includes(w) ? 1 : 0), 0);
      return { it, score };
    }).filter((h) => h.score > 0).sort((a, b) => b.score - a.score).map((h) => h.it);
  }, [q, index]);
  useEffect(() => { if (index && q && !hits.length) logMiss(q); }, [index, q, hits.length]);
  return (
    <div>
      <h1>Search: “{q}”</h1>
      {index === null ? <Loading /> : hits.length
        ? <div className="cards">{hits.map((it) => <Card key={it.slug} it={it} index={index} />)}</div>
        : <Empty text="Nothing yet. Auric has noted this search: missed searches become new pages." />}
    </div>
  );
}

/* ---------------------------------------------------------------- topic map */
export function MapPage({ index }) {
  const secs = allSections(index);
  const items = (index && index.items) || [];
  const W = 900, H = 900, cx = W / 2, cy = H / 2, R = 280;
  return (
    <div>
      <h1>Topic map</h1>
      <p className="lead">Every section around the centre, every page around its section. Tap any dot.</p>
      <svg className="map" viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Map of all topics">
        {secs.map((s, i) => {
          const a = (i / secs.length) * 2 * Math.PI - Math.PI / 2;
          const x = cx + R * Math.cos(a), y = cy + R * Math.sin(a);
          const mine = items.filter((it) => it.section === s.id);
          return (
            <g key={s.id}>
              <line x1={cx} y1={cy} x2={x} y2={y} stroke={s.color} strokeOpacity="0.35" strokeWidth="2" />
              {mine.map((it, j) => {
                const b = a + ((j - (mine.length - 1) / 2) * 0.16);
                const r2 = 85 + (j % 3) * 22;
                const px = x + r2 * Math.cos(b), py = y + r2 * Math.sin(b);
                return (
                  <a key={it.slug} href={`/a/${it.slug}`} onClick={(e) => { e.preventDefault(); go(`/a/${it.slug}`); }}>
                    <line x1={x} y1={y} x2={px} y2={py} stroke={s.color} strokeOpacity="0.3" />
                    <circle cx={px} cy={py} r="9" fill={s.color}><title>{it.title}</title></circle>
                  </a>
                );
              })}
              <a href={`/s/${s.id}`} onClick={(e) => { e.preventDefault(); go(`/s/${s.id}`); }}>
                <circle cx={x} cy={y} r="40" fill="var(--card)" stroke={s.color} strokeWidth="3" />
                <text x={x} y={y + 9} textAnchor="middle" fontSize="28">{s.icon}</text>
                <text x={x} y={y + 64} textAnchor="middle" fontSize="15" fill="var(--text)">{s.name.split(' & ')[0]}</text>
              </a>
            </g>
          );
        })}
        <circle cx={cx} cy={cy} r="56" fill="url(#core)" />
        <defs><radialGradient id="core"><stop offset="0" stopColor="#8b7cff" /><stop offset="1" stopColor="#4aa8ff" /></radialGradient></defs>
        <text x={cx} y={cy + 6} textAnchor="middle" fontSize="17" fontWeight="700" fill="#fff">TechVerse</text>
      </svg>
    </div>
  );
}

/* ---------------------------------------------------------------- timeline */
export function TimelinePage({ index }) {
  const events = ((index && index.items) || []).flatMap((it) => (it.dates || []).map((d) => ({ ...d, it })))
    .filter((e) => /^-?\d{1,4}/.test(String(e.year)))
    .sort((a, b) => parseInt(a.year, 10) - parseInt(b.year, 10));
  return (
    <div>
      <h1>Timeline of technology</h1>
      <p className="lead">Key dates from every page, in order. Each one comes from that page’s sources.</p>
      {index === null ? <Loading /> : events.length ? (
        <ol className="timeline">
          {events.map((e, i) => {
            const s = sectionById(e.it.section, index.sections || []);
            return (
              <li key={i} style={{ '--sec': s.color }}>
                <b>{e.year}</b>
                <div><p>{String(e.text).replace(/\s*\[\d+\]/g, '')}</p><Link to={`/a/${e.it.slug}`}>{s.icon} {e.it.title}</Link></div>
              </li>
            );
          })}
        </ol>
      ) : <Empty text="The timeline fills up as Auric writes pages." />}
    </div>
  );
}

/* ---------------------------------------------------------------- demos */
export function DemosPage({ id }) {
  const d = id && DEMOS[id];
  if (d) {
    const C = d.Component;
    return (
      <div>
        <nav className="crumbs"><Link to="/demos">Demos</Link> › {d.name}</nav>
        <h1>{d.name}</h1><p className="lead">{d.about}</p><C />
      </div>
    );
  }
  return (
    <div>
      <h1>Live demos</h1>
      <p className="lead">Play with how technology works.</p>
      <div className="cards">{Object.entries(DEMOS).map(([k, x]) => <Link key={k} to={`/demos/${k}`} className="card"><b>{x.name}</b><span>{x.about}</span></Link>)}</div>
    </div>
  );
}

/* ---------------------------------------------------------------- quiz */
export function QuizPage({ index }) {
  const [a, setA] = useState(null);
  const [round, setRound] = useState(0);
  const pool = ((index && index.items) || []).filter((i) => i.quiz > 0);
  useEffect(() => {
    if (!pool.length) return;
    const it = pool[Math.floor(Math.random() * pool.length)];
    getArticle(it.slug).then(setA).catch(() => {});
  }, [index, round]); // eslint-disable-line react-hooks/exhaustive-deps
  return (
    <div>
      <h1>Quiz</h1>
      {index === null ? <Loading /> : !pool.length ? <Empty text="Quizzes appear as Auric writes pages." /> : !a ? <Loading /> : (
        <>
          <p className="lead">About: <Link to={`/a/${a.slug}`}>{a.title}</Link></p>
          <Quiz key={a.slug + round} items={a.quiz} />
          <button className="btn primary" onClick={() => { setA(null); setRound((r) => r + 1); }}>Next quiz →</button>
        </>
      )}
    </div>
  );
}

/* ---------------------------------------------------------------- how it's made */
export function AboutPage({ index }) {
  const [log, setLog] = useState(null);
  useEffect(() => { getHistory().then(setLog).catch(() => setLog([])); }, []);
  const icon = { publish: '📝', improve: '🛠️', review: '🔍', fail: '⚠️', subjects: '🧭', code: '💻' };
  return (
    <div className="about">
      <h1>How TechVerse is made</h1>
      <p className="lead">Every page is researched, written and checked by <b>Auric</b>, an AI Saad built, running on his own computer. No other AI writes here.</p>
      <ol className="steps">
        <li>Auric picks a subject, preferring sections with few pages and searches that found nothing.</li>
        <li>It reads at least 3 independent sources (Wikipedia, Wikidata, Stack Exchange, OpenAlex, official docs) and notes where every fact comes from.</li>
        <li>It writes the page in its own words, one idea at a time, with examples.</li>
        <li>It checks every sentence against the sources: a fact, number or date that no source supports is left out. Links are opened, copied passages are rejected.</li>
        <li>Only then is the page published, and the change is logged below. Each day it also improves one existing page.</li>
      </ol>
      <h2>Latest changes</h2>
      {log === null ? <Loading /> : log.length ? (
        <ul className="log">{log.map((h) => (
          <li key={h.id}><span>{icon[h.kind] || '•'}</span><div>
            <b>{h.subject}</b> <small>{new Date(h.time).toLocaleString()}</small>
            <p>{h.change}{h.why ? ` — ${h.why}` : ''}</p>
          </div></li>
        ))}</ul>
      ) : <Empty text="Nothing logged yet." />}
      <p className="muted">{(index && index.items.length) || 0} pages so far.</p>
    </div>
  );
}

export const NotFound = () => <Empty text="This page doesn’t exist." />;
