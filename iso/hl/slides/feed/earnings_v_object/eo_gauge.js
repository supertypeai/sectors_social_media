// Earnings (object direction), slide 4: a pressure gauge of year-on-year profit growth. Peers in the same
// sub-sector are the small marks on the dial; the needle is this company; the sector median is a tick.
// DATA.slide: { title, sub, sym, logo, g, gs, med, meds, peers: [g…], line }
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = D.direction === "buy" ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.5, fy: 280, reach: 240, op: 0.22 });
frame(D);

type(svg, M, 74, S.title, "title", { fill: TONE.hi });
type(svg, M, 90, `YoY profit growth, ${S.sub} peers`, "body", { fill: TONE.muted });

// the dial's range: from −100% to a round top that holds the company (outliers pin to the end)
const all = [S.g, S.med, ...S.peers];
const lo = -1, hi = Math.max(1, Math.ceil(Math.min(5, Math.max(S.g, S.med) * 1.15) * 2) / 2);
const cx = W / 2, cy = 292, R = 124;
const ang = (v) => Math.PI * (1 - (Math.max(lo, Math.min(hi, v)) - lo) / (hi - lo)); // lo → left, hi → right
const pt = (v, r) => [cx + r * Math.cos(ang(v)), cy - r * Math.sin(ang(v))];
const arc = (r, v0, v1) => { const [x0, y0] = pt(v0, r), [x1, y1] = pt(v1, r); return `M${x0} ${y0}A${r} ${r} 0 0 1 ${x1} ${y1}`; };
const g = mk("g", {}, svg);
glow(cx, cy - 40, 150, 90, 0.1);
// bezel: two arcs and a base plate
mk("path", { d: arc(R + 12, lo, hi), class: "nf", style: `stroke:${TONE.edge};stroke-width:1.2px` }, g);
mk("path", { d: arc(R - 26, lo, hi), class: "nf lo" }, g);
mk("path", { d: `M${cx - R - 12} ${cy}L${cx + R + 12} ${cy}`, style: `stroke:${TONE.edge};stroke-width:1.2px` }, g);
// minor ticks every 10%, majors on round values
for (let v = lo; v <= hi + 1e-9; v += 0.1) {
  const major = Math.abs(v * 2 - Math.round(v * 2)) < 1e-6;
  const [x0, y0] = pt(v, R + 12), [x1, y1] = pt(v, R + (major ? 1 : 6));
  mk("line", { x1: x0, y1: y0, x2: x1, y2: y1, style: `stroke:${major ? TONE.edge : TONE.mid};stroke-width:${major ? 1 : 0.6}px` }, g);
  if (major && (Math.abs(v - Math.round(v)) < 1e-6)) {
    const [tx, ty] = pt(v, R + 22);
    type(g, tx, ty + 3, `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(Math.round(v * 100))}%`, "label", { fill: TONE.faint, size: 6.6, anchor: "middle" });
  }
}
// the healthy side of zero, an accent hairline
mk("path", { d: arc(R - 12, D.direction === "buy" ? 0 : lo, D.direction === "buy" ? hi : 0), class: "nf", style: "stroke:var(--acc);stroke-width:.8px;opacity:.5" }, g);
// peers: small dots inside the dial
for (const v of S.peers) { const [x, y] = pt(v, R - 12); mk("circle", { cx: x, cy: y, r: 2.4, style: `fill:${TONE.ground};stroke:${TONE.muted};stroke-width:.9px` }, g); }
// the median: a long tick and its value
{ const [x0, y0] = pt(S.med, R - 30), [x1, y1] = pt(S.med, R + 14);
  mk("line", { x1: x0, y1: y0, x2: x1, y2: y1, style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:2 2` }, g);
  const [tx, ty] = pt(S.med, R - 44);
  type(g, tx, ty, "median", "label", { fill: TONE.muted, size: 6.6, anchor: "middle" });
  type(g, tx, ty + 9, S.meds, "label", { fill: TONE.hi, size: 8, weight: 650, anchor: "middle" }); }
// the needle
{ const [nx, ny] = pt(S.g, R + 4), a = ang(S.g), w = 4.5;
  const bx = cx + w * Math.sin(a), byy = cy + w * Math.cos(a), b2x = cx - w * Math.sin(a), b2y = cy - w * Math.cos(a);
  mk("path", { d: `M${bx} ${byy}L${nx} ${ny}L${b2x} ${b2y}Z`, style: "fill:var(--acc);stroke:none" }, g);
  mk("circle", { cx, cy, r: 15, style: `fill:${TONE.ground};stroke:var(--acc);stroke-width:1.2px` }, g);
  logoChip(g, cx, cy, 11, S.logo, S.sym);
  if (S.g > hi) type(g, nx - 4, ny + 12, "off the dial →", "label", { fill: INK, size: 6.6, anchor: "end" }); }

type(svg, cx, cy + 46, S.gs, "num", { size: 40, weight: 620, fill: INK, anchor: "middle" });
type(svg, cx, cy + 60, `${S.sym}, this quarter vs a year ago`.toUpperCase(), "caps", { fill: TONE.muted, size: 6.4, weight: 700, anchor: "middle" });
type(svg, cx, cy + 92, S.line, "body", { fill: TONE.hi, anchor: "middle", weight: 520 });
grain(0.08);
