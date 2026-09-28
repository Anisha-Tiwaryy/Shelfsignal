// Small dependency-free SVG line chart.
interface Series { name: string; color: string; points: [number, number][]; dashed?: boolean }
interface Props { series: Series[]; xLabels?: string[]; yMin?: number; yMax?: number; height?: number; yFormat?: (v: number) => string }

export function LineChart({ series, xLabels, yMin, yMax, height = 220, yFormat = v => v.toFixed(0) }: Props) {
  const W = 640, H = height, L = 44, R = 12, T = 12, B = 28;
  const xs = series.flatMap(s => s.points.map(p => p[0]));
  const ys = series.flatMap(s => s.points.map(p => p[1]));
  if (!xs.length) return <p className="muted">No data</p>;
  const x0 = Math.min(...xs), x1 = Math.max(...xs);
  const y0 = yMin ?? Math.min(...ys), y1 = yMax ?? Math.max(...ys);
  const sx = (x: number) => L + ((x - x0) / (x1 - x0 || 1)) * (W - L - R);
  const sy = (y: number) => T + (1 - (y - y0) / (y1 - y0 || 1)) * (H - T - B);
  const ticks = [0, 0.25, 0.5, 0.75, 1].map(f => y0 + f * (y1 - y0));
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="chart" role="img">
      {ticks.map(t => (
        <g key={t}>
          <line x1={L} x2={W - R} y1={sy(t)} y2={sy(t)} className="grid" />
          <text x={L - 6} y={sy(t) + 4} textAnchor="end" className="tick">{yFormat(t)}</text>
        </g>
      ))}
      {xLabels?.map((lab, i) => i % 2 === 0 && (
        <text key={lab} x={sx(i)} y={H - 8} textAnchor="middle" className="tick">{lab}</text>
      ))}
      {series.map(s => (
        <polyline key={s.name} fill="none" stroke={s.color} strokeWidth={2}
          strokeDasharray={s.dashed ? "5 4" : undefined}
          points={s.points.map(p => `${sx(p[0])},${sy(p[1])}`).join(" ")} />
      ))}
    </svg>
  );
}
