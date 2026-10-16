// Focused charts: one chart per slide, as big as the slide allows, with the story written on it.
// Rules: no legend (label the thing itself), at most three value labels on an axis, gridlines faint,
// one accent for what the slide is about, numbers on the chart large enough to read on a phone.
// Pasted after style.js; draws into the same 360 × 450 svg.

/** A linear scale from a domain to a range. */
const scale = (d0, d1, r0, r1) => (v) => r0 + ((v - d0) / (d1 - d0 || 1)) * (r1 - r0);
const dayOf = (s) => Date.parse(String(s).slice(0, 10) + "T00:00:00Z");
const fmtDay = (t) => new Date(t).toLocaleDateString("en-GB", { day: "numeric", month: "short", timeZone: "UTC" });
const fmtMonth = (t) => new Date(t).toLocaleDateString("en-GB", { month: "short", timeZone: "UTC" });
const rupiah = (v) => `Rp ${Math.round(v).toLocaleString("en-US")}`;
/** Round numbers for an axis: three ticks covering [lo, hi]. */
function niceTicks(lo, hi, n = 3) {
  const step0 = (hi - lo) / n, mag = 10 ** Math.floor(Math.log10(step0)), step = [1, 2, 2.5, 5, 10].map((m) => m * mag).find((s) => s >= step0);
  const out = [];
  for (let v = Math.ceil(lo / step) * step; v <= hi; v += step) out.push(+v.toFixed(6));
  return out;
}
/** Last close of each week: the shape of the price without the daily noise. [[t, v], …] in, same out. */
function weekly(px) {
  const out = new Map();
  for (const [t, v] of px) out.set(Math.floor((t / 864e5 + 3) / 7), [t, v]); // weeks start Monday
  return [...out.values()];
}
/** A smooth path through screen points (Catmull-Rom → cubic Bézier), no overshoot past neighbours. */
function smoothPath(pts) {
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2;
    const lo = Math.min(p1[1], p2[1]), hi = Math.max(p1[1], p2[1]), cl = (v) => Math.min(hi, Math.max(lo, v));
    d += `C${(p1[0] + (p2[0] - p0[0]) / 6).toFixed(1)} ${cl(p1[1] + (p2[1] - p0[1]) / 6).toFixed(1)} ${(p2[0] - (p3[0] - p1[0]) / 6).toFixed(1)} ${cl(p2[1] - (p3[1] - p1[1]) / 6).toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}
/** A soft vertical gradient (colour → transparent) for the area under a line; returns its url(). */
let gradId = 0;
function areaFill(color, top = 0.16) {
  const id = `ag${++gradId}`, lg = mk("linearGradient", { id, x1: 0, y1: 0, x2: 0, y2: 1 }, mk("defs", {}, svg));
  mk("stop", { offset: 0, "stop-color": color, "stop-opacity": top }, lg);
  mk("stop", { offset: 1, "stop-color": color, "stop-opacity": 0 }, lg);
  return `url(#${id})`;
}
/** A line with a soft area under it down to `base`; returns the path's d. */
function areaLine(g, pts, base, { color = TONE.hi, width = 1.7, fill = 0.14, smooth = true } = {}) {
  const d = smooth ? smoothPath(pts) : `M${pts.map((p) => p.join(" ")).join("L")}`;
  mk("path", { d: `${d}L${pts.at(-1)[0]} ${base}L${pts[0][0]} ${base}Z`, style: `fill:${areaFill(color, fill)};stroke:none` }, g);
  mk("path", { d, class: "nf", style: `stroke:${color};stroke-width:${width}px` }, g);
  return d;
}
/** A glowing marker dot. */
function glowDot(g, x, y, color = "var(--acc)", r = 3.6) {
  mk("circle", { cx: x, cy: y, r: r * 3, style: `fill:${color};fill-opacity:.14;stroke:none` }, g);
  mk("circle", { cx: x, cy: y, r: r * 1.8, style: `fill:${color};fill-opacity:.22;stroke:none` }, g);
  mk("circle", { cx: x, cy: y, r, style: `fill:${color};stroke:${TONE.ground};stroke-width:1.4px` }, g);
}
/** Screen y of a polyline at screen x (linear between points). */
function yAt(pts, x) {
  const i = pts.findIndex((p) => p[0] >= x);
  if (i <= 0) return pts[Math.max(0, i)][1];
  const [a, b] = [pts[i - 1], pts[i]];
  return a[1] + ((x - a[0]) / (b[0] - a[0] || 1)) * (b[1] - a[1]);
}
const rp = (v) => `Rp ${Math.round(v).toLocaleString("en-US")}`;

/** The chart's plot box, shared by every chart: wide, and most of the slide's height. */
const PLOT = { x0: M, x1: W - M, y0: 176, y1: 392 };

/** Faint horizontal gridlines with their values set small inside the plot, at the right edge. */
function yGrid(g, ys, ticks, fmt) {
  for (const v of ticks) {
    const y = ys(v);
    mk("line", { x1: PLOT.x0, y1: y, x2: PLOT.x1, y2: y, class: "lo thin" }, g);
    type(g, PLOT.x1, y - 3, fmt(v), "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
  }
}
/** Month names under the plot, one per month boundary. */
function xMonths(g, xs, t0, t1) {
  const d = new Date(t0);
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() + 1);
  for (; d.getTime() <= t1; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const x = xs(d.getTime());
    mk("line", { x1: x, y1: PLOT.y1, x2: x, y2: PLOT.y1 + 3, class: "lo thin" }, g);
    type(g, x, PLOT.y1 + 13, fmtMonth(d.getTime()), "label", { fill: TONE.faint, size: 6.6, anchor: "middle" });
  }
}
/** A callout: a short rule from a point to a two-line label, set where it fits. */
function callout(g, [x, y], [tx, ty], head, sub, { anchor = "start", headFill = TONE.hi, size = 13 } = {}) {
  mk("path", { d: `M${x} ${y}L${tx} ${ty}`, class: "nf thin", style: `stroke:${TONE.edge}` }, g);
  const dx = anchor === "start" ? 3 : anchor === "end" ? -3 : 0;
  type(g, tx + dx, ty - 4, head, "label", { fill: headFill, size, weight: 650, anchor });
  if (sub) type(g, tx + dx, ty + 7, sub, "label", { fill: TONE.muted, size: 7, anchor });
}
