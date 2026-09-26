import { useId, useRef, useState } from "react";

export interface Point { label: string; value: number | null; note?: string }

interface Props {
  points: Point[];
  format: (v: number) => string;
  target?: { value: number; label: string };
  min?: number;
  max?: number;
  height?: number;
  title: string;
}

/**
 * Single-series monthly line: 2px line, 8px markers, recessive grid, dashed target,
 * crosshair + tooltip snapping to the nearest month. Gaps stay gaps (no data ≠ 0).
 */
export function LineChart({ points, format, target, min, max, height = 150, title }: Props) {
  const W = 360;
  const H = height;
  const vals = points.map((p) => p.value).filter((v): v is number => v !== null);
  let lo = min ?? Math.min(...vals, target?.value ?? Infinity);
  let hi = max ?? Math.max(...vals, target?.value ?? -Infinity);
  if (!isFinite(lo) || !isFinite(hi)) {
    lo = 0;
    hi = 1;
  }
  if (hi === lo) {
    hi = hi + (Math.abs(hi) || 1) * 0.1;
    lo = lo - (Math.abs(lo) || 1) * 0.1;
  }
  const ticks = [lo, (lo + hi) / 2, hi];
  const widest = Math.max(...ticks.map((t) => format(t).length));
  const pad = { l: Math.max(30, widest * 5.6 + 8), r: 10, t: 12, b: 22 };
  const x = (i: number) => pad.l + (i * (W - pad.l - pad.r)) / Math.max(points.length - 1, 1);
  const y = (v: number) => pad.t + (1 - (v - lo) / (hi - lo)) * (H - pad.t - pad.b);
  const [hover, setHover] = useState<number | null>(null);
  const svgRef = useRef<SVGSVGElement>(null);
  const tid = useId();

  const segments: string[] = [];
  let cur = "";
  points.forEach((p, i) => {
    if (p.value === null) {
      if (cur) segments.push(cur);
      cur = "";
    } else cur += `${cur ? "L" : "M"}${x(i).toFixed(1)},${y(p.value).toFixed(1)}`;
  });
  if (cur) segments.push(cur);

  const onMove = (e: React.PointerEvent) => {
    const r = svgRef.current!.getBoundingClientRect();
    const px = ((e.clientX - r.left) / r.width) * W;
    const i = Math.round(((px - pad.l) / (W - pad.l - pad.r)) * (points.length - 1));
    setHover(Math.max(0, Math.min(points.length - 1, i)));
  };

  const hp = hover !== null ? points[hover] : null;
  return (
    <div className="chart">
      <svg
        ref={svgRef}
        viewBox={`0 0 ${W} ${H}`}
        role="img"
        aria-label={title}
        onPointerMove={onMove}
        onPointerLeave={() => setHover(null)}
        tabIndex={0}
        onKeyDown={(e) => {
          if (e.key === "ArrowRight") setHover((h) => Math.min(points.length - 1, (h ?? -1) + 1));
          if (e.key === "ArrowLeft") setHover((h) => Math.max(0, (h ?? points.length) - 1));
        }}
        onBlur={() => setHover(null)}
      >
        {ticks.map((t, i) => (
          <g key={i}>
            <line x1={pad.l} x2={W - pad.r} y1={y(t)} y2={y(t)} className="grid" />
            <text x={pad.l - 6} y={y(t) + 4} className="tick" textAnchor="end">{format(t)}</text>
          </g>
        ))}
        {points.map((p, i) =>
          i % 2 === 0 ? (
            <text key={i} x={x(i)} y={H - 6} className="tick" textAnchor="middle">{p.label.slice(0, 3)}</text>
          ) : null,
        )}
        {target && (
          <g>
            <line x1={pad.l} x2={W - pad.r} y1={y(target.value)} y2={y(target.value)} className="target" />
            <text x={W - pad.r} y={y(target.value) - 4} className="tick" textAnchor="end">{target.label}</text>
          </g>
        )}
        {segments.map((d, i) => <path key={i} d={d} className="line" />)}
        {points.map((p, i) => (p.value === null ? null : <circle key={i} cx={x(i)} cy={y(p.value)} r={4} className="dotm" />))}
        {hover !== null && <line x1={x(hover)} x2={x(hover)} y1={pad.t} y2={H - pad.b} className="crosshair" />}
      </svg>
      {hp && (
        <div className="tooltip" id={tid} style={{ left: `${(x(hover!) / W) * 100}%` }} role="tooltip">
          <strong>{hp.value === null ? "Pas de donnée" : format(hp.value)}</strong>
          <span>{hp.label}{hp.note ? ` · ${hp.note}` : ""}</span>
        </div>
      )}
    </div>
  );
}

export function HBars({ items, format, title }: { items: { label: string; value: number }[]; format: (v: number) => string; title: string }) {
  const max = Math.max(...items.map((i) => i.value), 1);
  return (
    <div className="hbars" role="img" aria-label={title}>
      {items.map((it) => (
        <div className="hbar" key={it.label} title={`${it.label} : ${format(it.value)}`} tabIndex={0}>
          <span className="hbar-label">{it.label}</span>
          <span className="hbar-track"><span className="hbar-fill" style={{ width: `${(it.value / max) * 100}%` }} /></span>
          <span className="hbar-value">{format(it.value)}</span>
        </div>
      ))}
    </div>
  );
}
