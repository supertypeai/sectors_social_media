// Earnings (data-led), slide 3: is the new level normal? Net margin (profit per Rp 100 of sales) every
// quarter since 2020 as a line, the company's usual range (middle half of its quarters) as a soft band, and
// this quarter as the glowing dot at the end, read off against the band.
// DATA.slide: { title, sub, series: [{label, m}], lo, hi, med, cur, verdict }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
const ty = para(svg, M, 74, S.title, "title");
type(svg, M, ty + 18, S.sub, "body", { fill: TONE.muted, size: 8.5 });

// the big read-out
typeRun(svg, M - 2, ty + 72, [[`Rp ${(S.cur * 100).toFixed(0)}`, 46, 400, TONE.hi], [" per Rp 100 of sales", 9, 500, TONE.muted]]);

const P = { x0: M, x1: W - M - 6, y0: 186, y1: 352 }, n = S.series.length;
const vals = S.series.map((q) => q.m), vmin = Math.min(0, ...vals, S.lo), vmax = Math.max(...vals, S.hi);
const pad = (vmax - vmin) * 0.1;
const ys = scale(vmin - (vmin < 0 ? pad : 0), vmax + pad, P.y1, P.y0), xs = (i) => P.x0 + (i / (n - 1)) * (P.x1 - P.x0);
const g = mk("g", {}, svg);
// the usual range
mk("rect", { x: P.x0, y: ys(S.hi), width: P.x1 - P.x0, height: ys(S.lo) - ys(S.hi), style: `fill:${TONE.hi};fill-opacity:.05;stroke:none` }, g);
for (const v of [S.lo, S.hi]) mk("line", { x1: P.x0, y1: ys(v), x2: P.x1, y2: ys(v), style: `stroke:${TONE.faint};stroke-width:.6px;stroke-dasharray:1.5 3` }, g);
type(g, P.x0 + 2, ys(S.hi) - 4, `Usual range  Rp ${(S.lo * 100).toFixed(0)}–${(S.hi * 100).toFixed(0)}`, "label", { fill: TONE.muted, size: 6.8 });
if (vmin < 0) mk("line", { x1: P.x0, y1: ys(0), x2: P.x1, y2: ys(0), style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
// the line
const pts = S.series.map((q, i) => [xs(i), ys(q.m)]);
mk("path", { d: smoothPath(pts), class: "nf", style: `stroke:${TONE.edge};stroke-width:1.3px` }, g);
// the same quarter a year ago, a quiet ring
const pi = n - 5;
if (pi >= 0) {
  mk("circle", { cx: pts[pi][0], cy: pts[pi][1], r: 2.2, style: `fill:${TONE.ground};stroke:${TONE.hi};stroke-width:.9px` }, g);
  const ly = pts[pi][1] + (pts[pi][1] > (P.y0 + P.y1) / 2 ? 14 : -8);
  type(g, pts[pi][0], ly, `${S.series[pi].label.replace("-20", " '")}  Rp ${(S.series[pi].m * 100).toFixed(0)}`, "label", { fill: TONE.muted, size: 6.8, anchor: "middle" });
}
glowDot(g, pts[n - 1][0], pts[n - 1][1], "var(--acc)", 3);
// years
S.series.forEach((q, i) => { if (q.label.startsWith("Q1")) type(g, xs(i), P.y1 + 14, q.label.slice(-4), "label", { fill: TONE.faint, size: 6.6, anchor: "middle" }); });
para(svg, M, 392, S.verdict, "body", { maxW: W - 2 * M, fill: TONE.hi });
grain(0.07);
