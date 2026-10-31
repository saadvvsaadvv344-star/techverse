import { useEffect, useState } from 'react';

// A tiny router: real URLs (/a/binary-numbers), back/forward buttons work, no library needed.
const listeners = new Set();
export function go(to) {
  if (to === location.pathname + location.search) return;
  history.pushState(null, '', to);
  listeners.forEach((f) => f());
  window.scrollTo({ top: 0 });
}
addEventListener('popstate', () => listeners.forEach((f) => f()));

export function useRoute() {
  const [, tick] = useState(0);
  useEffect(() => {
    const f = () => tick((n) => n + 1);
    listeners.add(f);
    return () => listeners.delete(f);
  }, []);
  const parts = location.pathname.split('/').filter(Boolean).map(decodeURIComponent);
  return { parts, query: new URLSearchParams(location.search) };
}

export function Link({ to, children, className, ...rest }) {
  return (
    <a href={to} className={className} {...rest}
      onClick={(e) => {
        if (e.ctrlKey || e.metaKey || e.shiftKey || e.button !== 0) return;
        e.preventDefault();
        go(to);
      }}>{children}</a>
  );
}
