// Auric's design toolkit: small, tested building blocks so its effects are smooth, short and hard to get wrong.
// Import what you need:  import { enhance, useInView, useSpring, canHover, reducedMotion } from '../kit.js';
import { useEffect, useRef, useState } from 'react';

export const clamp = (v, a = 0, b = 1) => Math.min(b, Math.max(a, v));
export const lerp = (a, b, t) => a + (b - a) * t;
export const mapRange = (v, a, b, c, d) => c + ((v - a) * (d - c)) / (b - a || 1);
export const reducedMotion = () => matchMedia('(prefers-reduced-motion: reduce)').matches;
export const canHover = () => matchMedia('(hover: hover) and (pointer: fine)').matches;

/** Runs onElement(el) for every element matching `selector`, now AND whenever new ones appear (page changes).
 *  onElement may return a cleanup function. Returns a function that undoes everything. Each element is done once.
 *  Use it to restyle or animate existing parts of the site: add your own "ax-..." classes to them. */
export function enhance(selector, onElement) {
  const done = new Map();
  const scan = () => document.querySelectorAll(selector).forEach((el) => {
    if (!done.has(el)) done.set(el, onElement(el) || null);
  });
  scan();
  const mo = new MutationObserver(scan);
  mo.observe(document.body, { childList: true, subtree: true });
  return () => {
    mo.disconnect();
    done.forEach((undo) => { if (typeof undo === 'function') undo(); });
  };
}

export const easeOut = (t) => 1 - (1 - t) ** 3;

/** Animates a number (no React needed: use it inside enhance or event handlers). Returns a cancel function.
 *  animate({ from: 0, to: 1, duration: 600, onUpdate: (v) => { el.style.opacity = v; } }) */
export function animate({ from = 0, to = 1, duration = 600, ease = easeOut, onUpdate, onDone } = {}) {
  if (reducedMotion()) { if (onUpdate) onUpdate(to); if (onDone) onDone(); return () => {}; }
  let raf = 0;
  const t0 = performance.now();
  const step = (t) => {
    const k = clamp((t - t0) / duration);
    if (onUpdate) onUpdate(from + (to - from) * ease(k));
    if (k < 1) raf = requestAnimationFrame(step);
    else if (onDone) onDone();
  };
  raf = requestAnimationFrame(step);
  return () => cancelAnimationFrame(raf);
}

/** A spring you push around (no React needed: use it inside enhance or event handlers). Works with numbers or
 *  arrays of numbers. const s = springValue(([x, y]) => { el.style.transform = `translate(${x}px, ${y}px)`; }, { initial: [0, 0] });
 *  then s.set([dx, dy]) on pointermove and s.set([0, 0]) on pointerleave; s.stop() in the cleanup. */
export function springValue(onUpdate, { stiffness = 170, damping = 20, initial = 0 } = {}) {
  const arr = Array.isArray(initial);
  let v = arr ? [...initial] : [initial], vel = v.map(() => 0), target = [...v], raf = 0, last = 0;
  const out = () => onUpdate(arr ? [...v] : v[0]);
  const step = (t) => {
    const dt = Math.min(0.05, last ? (t - last) / 1000 : 0.016);
    last = t;
    let moving = false;
    v = v.map((x, i) => {
      vel[i] += (-stiffness * (x - target[i]) - damping * vel[i]) * dt;
      if (Math.abs(vel[i]) > 0.01 || Math.abs(x - target[i]) > 0.01) moving = true;
      return x + vel[i] * dt;
    });
    out();
    if (moving) raf = requestAnimationFrame(step);
    else { v = [...target]; out(); last = 0; raf = 0; }
  };
  return {
    set(t) {
      target = Array.isArray(t) ? [...t] : [t];
      if (reducedMotion()) { v = [...target]; out(); return; }
      if (!raf) raf = requestAnimationFrame(step);
    },
    stop() { cancelAnimationFrame(raf); raf = 0; },
  };
}

/** Calls fn(entry.isIntersecting, el) when elements matching selector enter / leave the screen. Returns cleanup. */
export function onVisible(selector, fn, { once = true, margin = '0px 0px -10% 0px' } = {}) {
  const io = new IntersectionObserver((entries) => entries.forEach((e) => {
    fn(e.isIntersecting, e.target);
    if (once && e.isIntersecting) io.unobserve(e.target);
  }), { rootMargin: margin });
  const undo = enhance(selector, (el) => { io.observe(el); });
  return () => { io.disconnect(); undo(); };
}

/** true while the element (a ref) is on screen. */
export function useInView(ref, { once = true, margin = '0px' } = {}) {
  const [seen, setSeen] = useState(false);
  useEffect(() => {
    const el = ref.current;
    if (!el) return undefined;
    const io = new IntersectionObserver(([e]) => {
      if (!once) setSeen(e.isIntersecting);
      else if (e.isIntersecting) { setSeen(true); io.disconnect(); }
    }, { rootMargin: margin });
    io.observe(el);
    return () => io.disconnect();
  }, [ref, once, margin]);
  return seen;
}

/** How far the page is scrolled: 0 at the top, 1 at the bottom (updates smoothly, once per frame). */
export function useScrollProgress() {
  const [p, setP] = useState(0);
  useEffect(() => {
    let raf = 0;
    const on = () => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => {
        const max = document.documentElement.scrollHeight - innerHeight;
        setP(max > 0 ? clamp(scrollY / max) : 0);
      });
    };
    on();
    addEventListener('scroll', on, { passive: true });
    addEventListener('resize', on);
    return () => { removeEventListener('scroll', on); removeEventListener('resize', on); cancelAnimationFrame(raf); };
  }, []);
  return p;
}

/** The mouse position in the window ({x, y} in px), once per frame. */
export function useMouse() {
  const [m, setM] = useState({ x: -1, y: -1 });
  useEffect(() => {
    let raf = 0;
    const on = (e) => {
      cancelAnimationFrame(raf);
      raf = requestAnimationFrame(() => setM({ x: e.clientX, y: e.clientY }));
    };
    addEventListener('pointermove', on, { passive: true });
    return () => { removeEventListener('pointermove', on); cancelAnimationFrame(raf); };
  }, []);
  return m;
}

/** A value that springs smoothly toward `target` (physics: stiffness / damping). Great for anything that follows. */
export function useSpring(target, { stiffness = 170, damping = 22 } = {}) {
  const [v, setV] = useState(target);
  const s = useRef({ v: target, vel: 0, raf: 0, last: 0 });
  useEffect(() => {
    const st = s.current;
    if (reducedMotion()) { st.v = target; setV(target); return undefined; }
    const step = (t) => {
      const dt = Math.min(0.05, st.last ? (t - st.last) / 1000 : 0.016);
      st.last = t;
      const f = -stiffness * (st.v - target) - damping * st.vel;
      st.vel += f * dt;
      st.v += st.vel * dt;
      setV(st.v);
      if (Math.abs(st.vel) > 0.001 || Math.abs(st.v - target) > 0.001) st.raf = requestAnimationFrame(step);
      else { st.v = target; setV(target); st.last = 0; }
    };
    cancelAnimationFrame(st.raf);
    st.raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(st.raf);
  }, [target, stiffness, damping]);
  return v;
}

/** Calls fn(seconds since start) every frame while mounted (stops itself if motion is reduced). */
export function useFrame(fn) {
  const ref = useRef(fn);
  ref.current = fn;
  useEffect(() => {
    if (reducedMotion()) return undefined;
    let raf = 0;
    const t0 = performance.now();
    const loop = (t) => { ref.current((t - t0) / 1000); raf = requestAnimationFrame(loop); };
    raf = requestAnimationFrame(loop);
    return () => cancelAnimationFrame(raf);
  }, []);
}
