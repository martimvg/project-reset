import { App, FUNNEL, PROGS, daysTo, reached } from '@/lib/constants';

/** How many applications reached each stage. */
export function Funnel({ apps }: { apps: App[] }) {
  const vals = FUNNEL.map(s => apps.filter(a => reached(a, s)).length), max = Math.max(1, ...vals);
  const W = 360, row = 30, H = FUNNEL.length * row + 8, x0 = 118, w = W - x0 - 40;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Applications reaching each stage">
      {FUNNEL.map((s, i) => {
        const y = i * row + 4, bw = Math.max(vals[i] ? 4 : 0, (vals[i] / max) * w);
        return (<g key={s}>
          <text className="lbl" x={x0 - 8} y={y + 16} textAnchor="end">{s}</text>
          <rect x={x0} y={y + 4} width={w} height={18} rx={9} fill="rgba(120,120,128,.10)" />
          <rect x={x0} y={y + 4} width={bw} height={18} rx={9} fill={s === 'Offer' ? '#34c759' : '#0071e3'} opacity={1 - i * 0.1} />
          <text x={x0 + bw + 6} y={y + 17}>{vals[i]}</text></g>);
      })}
    </svg>
  );
}

/** Applications sent per week over the last 10 weeks. */
export function Weeks({ apps }: { apps: App[] }) {
  const N = 10, weeks = Array.from({ length: N }, (_, k) => N - 1 - k);
  const vals = weeks.map(i => apps.filter(a => { if (!a.appliedOn) return false; const d = -(daysTo(a.appliedOn) as number); return d >= i * 7 && d < (i + 1) * 7; }).length);
  const max = Math.max(2, ...vals), W = 360, H = 180, b = 24, l = 26, cw = (W - l - 8) / N;
  const ticks = [0, Math.ceil(max / 2), max];
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label={`Applications sent per week, last ${N} weeks`}>
      {ticks.map(t => { const y = H - b - (t / max) * (H - b - 12); return (<g key={t}><line x1={l} x2={W - 4} y1={y} y2={y} stroke="rgba(60,60,67,.12)" /><text x={l - 6} y={y + 4} textAnchor="end">{t}</text></g>); })}
      {vals.map((v, i) => { const h = (v / max) * (H - b - 12), x = l + i * cw + cw * 0.18; return <rect key={i} x={x} y={H - b - h} width={cw * 0.64} height={h} rx={5} fill={i === N - 1 ? '#0071e3' : 'rgba(0,113,227,.45)'} />; })}
      <text x={l} y={H - 6}>{N} weeks ago</text><text x={W - 4} y={H - 6} textAnchor="end">This week</text>
    </svg>
  );
}

/** Applications sent, by programme type. */
export function Types({ apps }: { apps: App[] }) {
  const sent = apps.filter(a => a.stage !== 'Not started');
  const rows = PROGS.map(p => [p, sent.filter(a => (a.level || 'Summer Internship') === p).length] as [string, number]).filter(r => r[1] > 0);
  if (!rows.length) return <div className="empty">Applications you send will show here by type.</div>;
  const max = Math.max(1, ...rows.map(r => r[1])), W = 360, row = 30, H = rows.length * row + 8, x0 = 136, w = W - x0 - 36;
  return (
    <svg viewBox={`0 0 ${W} ${H}`} role="img" aria-label="Applications by programme type">
      {rows.map(([p, v], i) => { const y = i * row + 4, bw = (v / max) * w; return (<g key={p}><text className="lbl" x={x0 - 8} y={y + 16} textAnchor="end">{p}</text>
        <rect x={x0} y={y + 4} width={bw} height={18} rx={9} fill="#5856d6" opacity={0.8} /><text x={x0 + bw + 6} y={y + 17}>{v}</text></g>); })}
    </svg>
  );
}
