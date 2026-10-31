// Diagrams Auric "draws" as data ({ kind, items }): drawn here as SVG, sharp on every screen.
//   flow:    a -> b -> c            cycle:   a -> b -> c -> back to a
//   layers:  a stack, top to bottom compare: { items: [{ title, points: [...] }, { ... }] }
function lines(text, max = 18) {
  const out = [];
  let cur = '';
  for (const w of String(text).split(/\s+/)) {
    if ((cur + ' ' + w).trim().length > max && cur) { out.push(cur); cur = w; } else cur = (cur + ' ' + w).trim();
  }
  if (cur) out.push(cur);
  return out.slice(0, 4);
}
function Box({ x, y, w, h, text, color }) {
  const ls = lines(text, Math.max(10, Math.floor(w / 8.2)));
  return (
    <g>
      <rect x={x} y={y} width={w} height={h} rx="12" fill="var(--card)" stroke={color} strokeWidth="2" />
      {ls.map((l, i) => (
        <text key={i} x={x + w / 2} y={y + h / 2 + (i - (ls.length - 1) / 2) * 17 + 5} textAnchor="middle" fill="var(--text)" fontSize="14">{l}</text>
      ))}
    </g>
  );
}
const Arrow = ({ x1, y1, x2, y2, color }) => (
  <line x1={x1} y1={y1} x2={x2} y2={y2} stroke={color} strokeWidth="2.5" markerEnd="url(#tv-arrow)" />
);

export default function Diagram({ d, color = '#4aa8ff' }) {
  const raw = (d.items || []).slice(0, 8);
  const items = d.kind === 'compare' ? raw : raw.map((i) => (typeof i === 'string' ? i : String((i && i.title) || '')));
  const defs = (
    <defs><marker id="tv-arrow" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto-start-reverse">
      <path d="M0 0 L10 5 L0 10 z" fill={color} /></marker></defs>
  );
  const label = `${d.kind} diagram: ${items.map((i) => (typeof i === 'string' ? i : i.title)).join(', ')}`;

  if (d.kind === 'compare' && items.length >= 2) {
    const [a, b] = items;
    const rows = Math.max((a.points || []).length, (b.points || []).length);
    const H = 70 + rows * 46;
    return (
      <svg className="diagram" viewBox={`0 0 640 ${H}`} role="img" aria-label={label}>
        {[a, b].map((side, k) => (
          <g key={k}>
            <rect x={k * 330} y="0" width="310" height={H} rx="16" fill="var(--card)" stroke={color} strokeWidth="2" />
            <text x={k * 330 + 155} y="38" textAnchor="middle" fill={color} fontSize="18" fontWeight="700">{side.title}</text>
            {(side.points || []).map((p, i) => lines(p, 34).slice(0, 2).map((l, j) => (
              <text key={`${i}-${j}`} x={k * 330 + 20} y={76 + i * 46 + j * 17} fill="var(--text)" fontSize="14">{j === 0 ? '• ' : '  '}{l}</text>
            )))}
          </g>
        ))}
      </svg>
    );
  }
  if (d.kind === 'layers') {
    const H = items.length * 64;
    return (
      <svg className="diagram" viewBox={`0 0 640 ${H}`} role="img" aria-label={label}>
        {items.map((t, i) => <Box key={i} x={40 + i * 8} y={i * 64 + 4} w={560 - i * 16} h={54} text={t} color={color} />)}
      </svg>
    );
  }
  if (d.kind === 'cycle') {
    const n = items.length, R = 150, cx = 320, cy = 200;
    const pts = items.map((_, i) => [cx + R * Math.cos((i / n) * 2 * Math.PI - Math.PI / 2), cy + R * Math.sin((i / n) * 2 * Math.PI - Math.PI / 2)]);
    return (
      <svg className="diagram" viewBox="0 0 640 400" role="img" aria-label={label}>
        {defs}
        {pts.map(([x, y], i) => {
          const [x2, y2] = pts[(i + 1) % n];
          const f = 0.32;
          return <Arrow key={`a${i}`} x1={x + (x2 - x) * f} y1={y + (y2 - y) * f} x2={x2 - (x2 - x) * f} y2={y2 - (y2 - y) * f} color={color} />;
        })}
        {pts.map(([x, y], i) => <Box key={i} x={x - 75} y={y - 30} w={150} h={60} text={items[i]} color={color} />)}
      </svg>
    );
  }
  // flow (default): two per row on phones would be too small, so it zig-zags in rows of 3
  const per = 3, W = 180, Hb = 74, gx = 50, gy = 50;
  const rows = Math.ceil(items.length / per);
  return (
    <svg className="diagram" viewBox={`0 0 ${per * W + (per - 1) * gx} ${rows * Hb + (rows - 1) * gy}`} role="img" aria-label={label}>
      {defs}
      {items.map((t, i) => {
        const r = Math.floor(i / per), c = r % 2 ? per - 1 - (i % per) : i % per;
        const x = c * (W + gx), y = r * (Hb + gy);
        const next = i + 1 < items.length ? (() => {
          const r2 = Math.floor((i + 1) / per), c2 = r2 % 2 ? per - 1 - ((i + 1) % per) : (i + 1) % per;
          return [c2 * (W + gx), r2 * (Hb + gy)];
        })() : null;
        return (
          <g key={i}>
            {next && (next[1] === y
              ? <Arrow x1={next[0] > x ? x + W + 4 : x - 4} y1={y + Hb / 2} x2={next[0] > x ? next[0] - 6 : next[0] + W + 6} y2={y + Hb / 2} color={color} />
              : <Arrow x1={x + W / 2} y1={y + Hb + 4} x2={x + W / 2} y2={next[1] - 6} color={color} />)}
            <Box x={x} y={y} w={W} h={Hb} text={`${i + 1}. ${t}`} color={color} />
          </g>
        );
      })}
    </svg>
  );
}
