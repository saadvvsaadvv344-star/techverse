import { useEffect, useMemo, useState } from 'react';
import { getArticle, countView } from './api.js';
import { Link } from './router.jsx';
import { sectionById } from './sections.js';
import Diagram from './Diagram.jsx';
import Quiz from './Quiz.jsx';
import { DEMOS } from './demos/index.jsx';

/** Text with [n] citations -> text + superscript links to the source list; glossary words get their meaning on hover. */
function Rich({ text, terms }) {
  const parts = String(text || '').split(/(\[\d+\])/g);
  return parts.map((p, i) => {
    const m = /^\[(\d+)\]$/.exec(p);
    if (m) return <sup key={i}><a href={`#src-${m[1]}`} className="cite">{m[1]}</a></sup>;
    return <Terms key={i} text={p} terms={terms} />;
  });
}
function Terms({ text, terms }) {
  if (!terms.length) return text;
  const re = new RegExp(`\\b(${terms.map((t) => t.term.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')).join('|')})\\b`, 'i');
  const out = [];
  let rest = text;
  let k = 0;
  while (rest) {
    const m = re.exec(rest);
    if (!m) { out.push(rest); break; }
    const t = terms.find((x) => x.term.toLowerCase() === m[1].toLowerCase());
    out.push(rest.slice(0, m.index));
    out.push(<abbr key={k++} title={t.def} tabIndex={0}>{m[1]}</abbr>);
    rest = rest.slice(m.index + m[1].length);
  }
  return out;
}

const fmtDate = (s) => { try { return new Date(s).toLocaleDateString(undefined, { year: 'numeric', month: 'long', day: 'numeric' }); } catch { return s; } };

export default function Article({ slug, index }) {
  const [a, setA] = useState(undefined);
  useEffect(() => {
    setA(undefined);
    getArticle(slug).then((x) => { setA(x); if (x) countView(slug); }).catch(() => setA(null));
  }, [slug]);
  const terms = useMemo(() => (a && a.glossary) || [], [a]);
  useEffect(() => { if (a) document.title = `${a.title} · TechVerse`; return () => { document.title = 'TechVerse'; }; }, [a]);

  if (a === undefined) return <div className="loading" aria-busy="true"><span /><span /><span /></div>;
  if (!a) return <div className="empty"><h1>Not written yet</h1><p>Auric hasn’t written this page yet. <Link to="/">Back home</Link></p></div>;
  const sec = sectionById(a.section, (index && index.sections) || []);
  const Demo = a.demo && DEMOS[a.demo] && DEMOS[a.demo].Component;
  const related = (a.related || []).map((s) => index && index.items.find((i) => i.slug === s)).filter(Boolean);

  return (
    <article className="article" style={{ '--sec': sec.color }}>
      <nav className="crumbs"><Link to="/">Home</Link> › <Link to={`/s/${sec.id}`}>{sec.icon} {sec.name}</Link></nav>
      <h1>{a.title}</h1>
      <p className="lead"><Rich text={a.summary} terms={[]} /></p>
      <div className="meta-line">
        <span>✍️ Written by Auric from {(a.sources || []).length} sources</span>
        {a.checked && <span>✅ {a.checked.claims} facts checked{a.checked.removed ? `, ${a.checked.removed} unsure ones left out` : ''}</span>}
        <span>🕒 Updated {fmtDate(a.updated)}</span>
        {a.status === 'weak' && <span className="weak">🛠️ Being improved</span>}
      </div>

      {(a.body || []).map((s, i) => (
        <section key={i} className="block">
          {s.h && <h2>{s.h}</h2>}
          {(s.p || []).map((p, j) => <p key={j}><Rich text={p} terms={terms} /></p>)}
        </section>
      ))}

      {a.how && a.how.length > 0 && (
        <section className="block">
          <h2>How it works</h2>
          <ol className="steps">{a.how.map((s, i) => <li key={i}><Rich text={s} terms={terms} /></li>)}</ol>
        </section>
      )}

      {a.diagram && a.diagram.items && a.diagram.items.length > 1 && (
        <section className="block"><h2>{a.diagram.title || 'At a glance'}</h2><Diagram d={a.diagram} color={sec.color} /></section>
      )}

      {Demo && (
        <section className="block demo-block"><h2>Try it: {DEMOS[a.demo].name}</h2><Demo /></section>
      )}

      {a.dates && a.dates.length > 0 && (
        <section className="block">
          <h2>Key dates</h2>
          <ul className="dates">{a.dates.map((d, i) => <li key={i}><b>{d.year}</b><span><Rich text={d.text} terms={[]} /></span></li>)}</ul>
        </section>
      )}

      {a.examples && a.examples.length > 0 && (
        <section className="block">
          <h2>Real examples</h2>
          <ul className="examples">{a.examples.map((e, i) => <li key={i}><Rich text={e} terms={terms} /></li>)}</ul>
        </section>
      )}

      {terms.length > 0 && (
        <section className="block">
          <h2>Glossary</h2>
          <dl className="glossary">{terms.map((t) => <div key={t.term}><dt>{t.term}</dt><dd>{t.def}</dd></div>)}</dl>
        </section>
      )}

      {a.quiz && a.quiz.length > 0 && <section className="block"><h2>Quick quiz</h2><Quiz items={a.quiz} /></section>}

      {a.disagree && a.disagree.length > 0 && (
        <section className="block note"><h2>Sources disagree</h2>{a.disagree.map((d, i) => <p key={i}><Rich text={d} terms={[]} /></p>)}</section>
      )}

      <section className="block sources">
        <h2>Sources</h2>
        <ol>{(a.sources || []).map((s, i) => (
          <li key={i} id={`src-${i + 1}`}><a href={s.url} target="_blank" rel="noopener noreferrer">{s.title}</a> <small>{s.site}</small></li>
        ))}</ol>
      </section>

      {related.length > 0 && (
        <section className="block">
          <h2>Read next</h2>
          <div className="cards small">{related.map((r) => <Link key={r.slug} to={`/a/${r.slug}`} className="card"><b>{r.title}</b><span>{r.summary}</span></Link>)}</div>
        </section>
      )}
    </article>
  );
}
