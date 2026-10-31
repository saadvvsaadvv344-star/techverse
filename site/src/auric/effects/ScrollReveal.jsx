import { useEffect } from 'react';

// Cards, sections and steps glide in as they scroll into view (new ones after a page change too).
export default function ScrollReveal() {
  useEffect(() => {
    if (matchMedia('(prefers-reduced-motion: reduce)').matches || !('IntersectionObserver' in window)) return undefined;
    const io = new IntersectionObserver((entries) => {
      entries.forEach((e) => { if (e.isIntersecting) { e.target.classList.add('ax-in'); io.unobserve(e.target); } });
    }, { rootMargin: '0px 0px -8% 0px' });
    const watch = () => document.querySelectorAll('.card:not(.ax-seen), .sec:not(.ax-seen), .block:not(.ax-seen), .steps li:not(.ax-seen)')
      .forEach((el) => { el.classList.add('ax-seen', 'ax-reveal'); io.observe(el); });
    watch();
    const mo = new MutationObserver(watch);
    mo.observe(document.getElementById('root'), { childList: true, subtree: true });
    return () => { io.disconnect(); mo.disconnect(); };
  }, []);
  return null;
}
