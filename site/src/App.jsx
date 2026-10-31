import { useEffect, useState } from 'react';
import { Link, go, useRoute } from './router.jsx';
import { getIndex } from './api.js';
import Article from './Article.jsx';
import LivePage from './Live.jsx';
import { SelfTest } from './Safe.jsx';
import { Safe } from './Boundary.jsx';
import { EFFECTS } from './auric/registry.js';
import { Home, SectionPage, SearchPage, MapPage, TimelinePage, DemosPage, QuizPage, AboutPage, NotFound } from './pages.jsx';

function useTheme() {
  const [theme, setTheme] = useState(() => document.documentElement.dataset.theme
    || (matchMedia('(prefers-color-scheme: light)').matches ? 'light' : 'dark'));
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    try { localStorage.setItem('tv-theme', theme); } catch { /* this visit only */ }
  }, [theme]);
  return [theme, () => setTheme((t) => (t === 'dark' ? 'light' : 'dark'))];
}

const NAV = [['/live', '🔴 Live'], ['/map', 'Topic map'], ['/timeline', 'Timeline'], ['/demos', 'Demos'], ['/quiz', 'Quiz'], ['/about', 'How it’s made']];

export default function App() {
  const { parts, query } = useRoute();
  const [theme, toggle] = useTheme();
  const [index, setIndex] = useState(null);
  const [q, setQ] = useState(query.get('q') || '');
  const [menu, setMenu] = useState(false);
  const [fx, setFx] = useState(true);              // the self-test switches Auric's effects off to test their cleanup
  useEffect(() => {
    const off = () => setFx(false);
    addEventListener('tv-unmount-effects', off);
    return () => removeEventListener('tv-unmount-effects', off);
  }, []);
  useEffect(() => { getIndex().then(setIndex).catch(() => setIndex({ items: [], error: true })); }, []);
  useEffect(() => { setMenu(false); }, [location.pathname]);

  const [page, arg] = parts;
  let body;
  if (query.get('selftest')) body = <SelfTest />;
  else if (!page) body = <Home index={index} />;
  else if (page === 's') body = <SectionPage id={arg} index={index} />;
  else if (page === 'a') body = <Article slug={arg} index={index} />;
  else if (page === 'search') body = <SearchPage q={query.get('q') || ''} index={index} />;
  else if (page === 'map') body = <MapPage index={index} />;
  else if (page === 'timeline') body = <TimelinePage index={index} />;
  else if (page === 'demos') body = <DemosPage id={arg} />;
  else if (page === 'quiz') body = <QuizPage index={index} />;
  else if (page === 'about') body = <AboutPage index={index} />;
  else if (page === 'live') body = <LivePage />;
  else body = <NotFound />;

  return (
    <div className="app">
      <Safe name="effects (cleanup)">{fx && EFFECTS.map(({ name, Component }) => <Safe key={name} name={`effect ${name}`}><Component /></Safe>)}</Safe>
      <header className="top">
        <Link to="/" className="brand" aria-label="TechVerse home">
          <img src="/favicon.svg" alt="" width="30" height="30" /><span>Tech<b>Verse</b></span>
        </Link>
        <form className="search" role="search" onSubmit={(e) => { e.preventDefault(); if (q.trim()) go(`/search?q=${encodeURIComponent(q.trim())}`); }}>
          <input type="search" value={q} onChange={(e) => setQ(e.target.value)} placeholder="Search technology…" aria-label="Search" />
        </form>
        <nav className={`nav${menu ? ' open' : ''}`}>
          {NAV.map(([to, label]) => <Link key={to} to={to} className={location.pathname.startsWith(to) ? 'on' : ''}>{label}</Link>)}
        </nav>
        <button className="icon" onClick={toggle} aria-label={`Switch to ${theme === 'dark' ? 'light' : 'dark'} mode`} title="Dark / light">
          {theme === 'dark' ? '☀️' : '🌙'}
        </button>
        <button className="icon menu-btn" onClick={() => setMenu((m) => !m)} aria-label="Menu" aria-expanded={menu}>☰</button>
      </header>
      <main className="main">{body}</main>
      <footer className="foot">
        <p>TechVerse is written by <b>Auric</b>, Saad’s AI: every fact comes from the sources listed on its page, and every page is checked before it’s published.</p>
        <p><Link to="/about">How it’s made</Link> · <Link to="/map">All topics</Link></p>
      </footer>
    </div>
  );
}
