// Earnings (object direction), slide 3: margin as a coin. Each coin is Rp 100 of sales; the slice lifted out
// of it is the part kept as profit. Last year's coin left, this year's right.
// DATA.slide: { title, why, sales, profit, prev: {label, m}, now: {label, m} }
const D = DATA, S = D.slide;
setAccent(D.direction);
const INK = D.direction === "buy" ? "#b2d2b9" : "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.5, fy: 230, reach: 240, op: 0.22 });
frame(D);

para(svg, M, 72, S.title, "title", { maxW: 300 });

/** A point on an iso ellipse at angle a (0 = right, 90 = toward the viewer). */
const at = (cx, cy, r, a) => [cx + r * Math.cos(a * Math.PI / 180), cy + r * 0.5 * Math.sin(a * Math.PI / 180)];
/** Wedge path on an ellipse: centre, radius, from a0 to a1 degrees (clockwise on screen). */
function wedge(cx, cy, r, a0, a1) {
  const [x0, y0] = at(cx, cy, r, a0), [x1, y1] = at(cx, cy, r, a1);
  return `M${cx} ${cy}L${x0} ${y0}A${r} ${r * 0.5} 0 ${a1 - a0 > 180 ? 1 : 0} 1 ${x1} ${y1}Z`;
}
function slicedCoin(g, cx, by, r, t, m, lit) {
  const ry = r * 0.5, ty = by - t, st = lit ? "var(--acc)" : TONE.edge;
  // the coin
  mk("path", { d: `M${cx - r} ${ty}L${cx - r} ${by}A${r} ${ry} 0 0 0 ${cx + r} ${by}L${cx + r} ${ty}Z`, style: `fill:${TONE.ground};stroke:${TONE.edge};stroke-width:1px` }, g);
  mk("ellipse", { cx, cy: ty, rx: r, ry, style: `fill:${TONE.ground};stroke:${TONE.edge};stroke-width:1px` }, g);
  mk("ellipse", { cx, cy: ty, rx: r * 0.8, ry: ry * 0.8, style: `fill:none;stroke:${TONE.mid};stroke-width:.6px` }, g);
  // the slice, facing the viewer, centred on the front
  const f = Math.max(0.006, Math.min(0.95, m)), a0 = 90 - f * 180, a1 = 90 + f * 180;
  mk("path", { d: wedge(cx, ty, r, a0, a1), style: `fill:${TONE.card};stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 2` }, g);
  // lifted out: pulled toward the viewer and up
  const lift = 30, push = 14, sx = cx, sy = ty + push - lift;
  // the slice's outer rim: a curved band along the front arc, t deep
  const [p0x, p0y] = at(sx, sy, r, a0), [p1x, p1y] = at(sx, sy, r, a1), big = a1 - a0 > 180 ? 1 : 0;
  mk("path", { d: wedge(sx, sy + t, r, a0, a1), style: `fill:${TONE.ground};stroke:${st};stroke-width:1px` }, g);
  mk("path", { d: `M${p0x} ${p0y}A${r} ${r * 0.5} 0 ${big} 1 ${p1x} ${p1y}L${p1x} ${p1y + t}A${r} ${r * 0.5} 0 ${big} 0 ${p0x} ${p0y + t}Z`,
    style: `fill:${TONE.ground};stroke:${st};stroke-width:1px` }, g);
  const tint = !lit ? "rgba(138,130,123,.14)" : D.direction === "sell" ? "rgba(192,113,89,.35)" : "rgba(129,167,137,.35)";
  mk("path", { d: wedge(sx, sy, r, a0, a1), style: `fill:${tint};stroke:${st};stroke-width:1.2px` }, g);
  return sy;
}

const r = 70, t = 13, by = 250;
const L = { x: 96, ...S.prev, lit: false }, Rr = { x: 264, ...S.now, lit: true };
para(svg, M, 120, "Each coin is Rp 100 of sales. The lifted slice is profit.", "body", { fill: TONE.muted, lh: 1.35 });
glow(Rr.x, by - 20, 110, 70, 0.12);
const g = mk("g", {}, svg);
for (const c of [L, Rr]) {
  slicedCoin(g, c.x, by, r, t, c.m, c.lit);
  const kept = c.m * 100, ks = kept < 1 ? kept.toFixed(1) : kept < 10 ? kept.toFixed(1).replace(/\.0$/, "") : kept.toFixed(0);
  type(g, c.x, by + 62, `Rp ${ks}`, "num", { size: c.lit ? 30 : 24, weight: c.lit ? 620 : 380, fill: c.lit ? INK : TONE.hi, anchor: "middle" });
  type(g, c.x, by + 76, `kept · ${c.label}`.toUpperCase(), "caps", { fill: c.lit ? INK : TONE.muted, size: 6.4, weight: 750, anchor: "middle" });
}
mk("path", { d: `M${W / 2 - 14} ${by + 54}L${W / 2 + 10} ${by + 54}M${W / 2 + 5} ${by + 50}L${W / 2 + 10} ${by + 54}L${W / 2 + 5} ${by + 58}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, svg);

// the cause in one line
const yb = 362;
const w1 = S.sales.length * 4.6 + 16;
mk("rect", { x: M, y: yb - 11, width: w1, height: 16, rx: 8, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px` }, svg);
type(svg, M + 8, yb, S.sales, "label", { fill: TONE.hi, size: 7.6, weight: 600 });
const w2 = S.profit.length * 4.6 + 16;
mk("rect", { x: M + w1 + 6, y: yb - 11, width: w2, height: 16, rx: 8, style: `fill:none;stroke:var(--acc);stroke-width:.8px` }, svg);
type(svg, M + w1 + 14, yb, S.profit, "label", { fill: INK, size: 7.6, weight: 650 });
para(svg, M, yb + 22, S.why, "body", { maxW: W - 2 * M, lh: 1.35, fill: TONE.muted });
grain(0.08);
