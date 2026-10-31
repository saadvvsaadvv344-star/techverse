import { useEffect } from 'react';

// A soft light follows the mouse over cards (only with a mouse: phones don't need it).
export default function Spotlight() {
  useEffect(() => {
    if (!matchMedia('(hover: hover)').matches) return undefined;
    const on = (e) => {
      const el = e.target.closest && e.target.closest('.card, .sec');
      if (!el) return;
      const r = el.getBoundingClientRect();
      el.style.setProperty('--mx', `${e.clientX - r.left}px`);
      el.style.setProperty('--my', `${e.clientY - r.top}px`);
    };
    addEventListener('pointermove', on, { passive: true });
    return () => removeEventListener('pointermove', on);
  }, []);
  return null;
}
