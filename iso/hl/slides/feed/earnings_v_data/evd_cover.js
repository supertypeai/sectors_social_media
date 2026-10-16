// Earnings (data-led), slide 1: the stretched timeline. Every quarter of profit since 2020 as a thin bar; this
// quarter lit in the accent; a ruler runs back from it to the last quarter that was as high (or as low), so
// "best since Q4 2022" is seen, not just read. The multiple sits above as the hook.
// DATA.slide: { sym, name, logo, hero, up, head, sub, series: [{label, v}], since, prev, now_s }
const D = DATA, S = D.slide, up = S.up;
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.8, fy: 120, reach: 260, op: 0.22 });
frame(D);

// the company
logoChip(svg, M + 13, 66, 13, S.logo, S.sym);
type(svg, M + 33, 70, S.sym, "label", { fill: TONE.hi, size: 13, weight: 800 });
type(svg, M + 33 + S.sym.length * 9.2 + 6, 70, S.name, "label", { fill: TONE.muted, size: 8 });

// the hook
type(svg, M - 3, 150, S.hero, "hero", { size: S.hero.length > 5 ? 70 : 84, weight: 560, fill: INK });
type(svg, M, 176, up ? "profit vs the same quarter last year" : "profit vs the same quarter last year", "label", { fill: TONE.muted, size: 8.6 });
para(svg, M, 204, S.head, "title", { maxW: W - 2 * M });

// the timeline
const B = { x0: M, x1: W - M, y0: 252, y1: 372 }, n = S.series.length, bw = (B.x1 - B.x0) / n;
const vmax = Math.max(...S.series.map((q) => q.v)), vmin = Math.min(0, ...S.series.map((q) => q.v));
const ys = scale(vmin, vmax, B.y1, B.y0), z = ys(0);
const xi = (i) => B.x0 + i * bw + bw / 2, last = n - 1;
const si = S.since ? S.series.findIndex((q) => q.label === S.since) : -1;
const pi = S.series.findIndex((q) => q.label === S.prev);
const g = mk("g", {}, svg);
mk("line", { x1: B.x0, y1: z, x2: B.x1, y2: z, style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
S.series.forEach((q, i) => {
  const lit = i === last, ref = i === si, pr = i === pi;
  const y = Math.min(ys(q.v), z), h = Math.max(1.2, Math.abs(ys(q.v) - z)), w = bw * (lit ? 0.72 : 0.56);
  const fill = lit ? "var(--acc)" : ref ? TONE.edge : pr ? TONE.edge : TONE.mid;
  mk("rect", { x: xi(i) - w / 2, y, width: w, height: h, rx: Math.min(1.6, w / 2), style: `fill:${fill};stroke:none;${pr && !ref ? "fill-opacity:.75" : ""}` }, g);
  // a year mark under each Q1
  if (q.label.startsWith("Q1")) type(g, xi(i) - bw * 0.3, B.y1 + 13, q.label.slice(-4), "label", { fill: TONE.faint, size: 6.6 });
});
// the ruler: from the top of this quarter back to the reference quarter (or to the start, if none)
const yNow = ys(S.series[last].v), x0 = si >= 0 ? xi(si) : B.x0;
mk("line", { x1: x0, y1: yNow, x2: xi(last) - bw * 0.5, y2: yNow, style: `stroke:${INK};stroke-width:.9px;stroke-dasharray:2 3` }, g);
if (si >= 0) {
  mk("circle", { cx: x0, cy: yNow, r: 2, style: `fill:${INK};stroke:none` }, g);
  const lbl = S.since.replace("-20", " '");
  const near = xi(last) - x0 < 60; // too close to this quarter's own label: set it under the ruler instead
  type(g, x0, near ? yNow + 12 : yNow - 7, lbl, "label", { fill: INK, size: 7.4, weight: 650, anchor: x0 < B.x0 + 30 ? "start" : "middle" });
}
glowDot(g, xi(last), yNow - 0.5, "var(--acc)", 2.6);
// this quarter's value above its bar, right-aligned to the plot
type(g, B.x1, yNow - 12, S.now_s, "label", { fill: TONE.hi, size: 10, weight: 700, anchor: "end" });
type(svg, M, B.y0 - 14, "Net profit, every quarter since " + S.series[0].label.slice(-4), "caps", { fill: TONE.faint });
type(svg, M, 404, S.sub, "label", { fill: TONE.muted, size: 7.4 });
grain(0.07);
