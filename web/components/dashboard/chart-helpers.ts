/**
 * Tiny dependency-free SVG path builders for the dashboard charts.
 *
 * Kept separate so every card draws curves the same way: a Catmull-Rom-ish
 * smoothing turned into cubic beziers, clamped so a spike never overshoots the
 * box. No charting library is pulled in — the landing page stays lean and these
 * paths render identically server- and client-side.
 */

export interface Point {
  x: number;
  y: number;
}

/** Map a series into a box of (width × height) with a little vertical padding. */
export function toPoints(
  values: number[],
  width: number,
  height: number,
  { min, max }: { min?: number; max?: number } = {},
): Point[] {
  const lo = min ?? Math.min(...values);
  const hi = max ?? Math.max(...values);
  const span = hi - lo || 1;
  const pad = height * 0.12;
  const usable = height - pad * 2;
  const step = values.length > 1 ? width / (values.length - 1) : width;
  return values.map((v, i) => ({
    x: i * step,
    y: pad + usable - ((v - lo) / span) * usable,
  }));
}

/** Smooth open line through the points. */
export function linePath(points: Point[]): string {
  if (points.length === 0) return "";
  if (points.length === 1) return `M ${points[0].x} ${points[0].y}`;
  let d = `M ${points[0].x.toFixed(2)} ${points[0].y.toFixed(2)}`;
  for (let i = 0; i < points.length - 1; i++) {
    const p0 = points[i - 1] ?? points[i];
    const p1 = points[i];
    const p2 = points[i + 1];
    const p3 = points[i + 2] ?? p2;
    const cp1x = p1.x + (p2.x - p0.x) / 6;
    const cp1y = p1.y + (p2.y - p0.y) / 6;
    const cp2x = p2.x - (p3.x - p1.x) / 6;
    const cp2y = p2.y - (p3.y - p1.y) / 6;
    d += ` C ${cp1x.toFixed(2)} ${cp1y.toFixed(2)}, ${cp2x.toFixed(2)} ${cp2y.toFixed(2)}, ${p2.x.toFixed(2)} ${p2.y.toFixed(2)}`;
  }
  return d;
}

/** Closed area under the same smooth line, dropped to the baseline. */
export function areaPath(points: Point[], height: number): string {
  if (points.length === 0) return "";
  const line = linePath(points);
  const last = points[points.length - 1];
  const first = points[0];
  return `${line} L ${last.x.toFixed(2)} ${height} L ${first.x.toFixed(2)} ${height} Z`;
}

/**
 * Arc segments for the donut/ring. Given slice values and a radius, returns
 * dasharray/offset pairs positioned around the circle so each segment can carry
 * its own stroke and a rounded cap with a gap.
 */
export function ringSegments(
  values: number[],
  radius: number,
  gapDeg = 3,
): { dashArray: string; dashOffset: number; fraction: number }[] {
  const total = values.reduce((a, b) => a + b, 0) || 1;
  const circumference = 2 * Math.PI * radius;
  let acc = 0;
  return values.map((v) => {
    const fraction = v / total;
    const gap = (gapDeg / 360) * circumference;
    const seg = Math.max(fraction * circumference - gap, 0.5);
    const dashArray = `${seg} ${circumference - seg}`;
    const dashOffset = -acc * circumference - gap / 2;
    acc += fraction;
    return { dashArray, dashOffset, fraction };
  });
}
