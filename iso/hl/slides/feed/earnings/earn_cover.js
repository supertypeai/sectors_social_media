// Earnings, slide 1 (the hook): the multiple huge, then this quarter's profit against the same quarter a year
// ago as two iso columns, true to scale; the company logo rides the new column as a 3D coin.
// DATA.slide: { sym, name, logo, sector, hero, up, prev: {label, v, s}, now: {label, v, s} }
const D = DATA, S = D.slide;
setAccent(D.direction);
const up = S.up, FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74", SIDE = up ? "#5f7d66" : "#8f5444", TOPF = up ? "#c5dccb" : "#e9b9a9";
dotField(0, 0, W, H, { fx: W * 0.7, fy: 360, reach: 280, op: 0.3 });
frame(D);

// the company
logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });

// the hook: the multiple, then one plain line
type(svg, M - 4, 156, S.hero, "hero", { size: S.hero.length > 5 ? 74 : 88, weight: 600, fill: INK });
type(svg, M, 180, up ? "more profit than a year ago" : "less profit than a year ago", "title", { size: 16, fill: TONE.hi });
type(svg, M, 196, `${S.now.label} vs ${S.prev.label}`, "label", { fill: TONE.muted, size: 8.5 });

// two iso columns on a floor, heights true to profit
const base = H - 58, maxH = base - 262, fw = 70, dx = 24, dy = 14;
const hv = (v) => Math.max(6, maxH * (v / Math.max(S.now.v, S.prev.v)));
const cols = [{ ...S.prev, x: M + 40, lit: false }, { ...S.now, x: W - M - fw - dx - 30, lit: true }];
mk("path", { d: `M${M - 6} ${base}L${W - M} ${base}`, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
cols.forEach((c) => {
  const h = hv(c.v), top = base - h, x = c.x;
  const front = c.lit ? FILL : "#4f5550", side = c.lit ? SIDE : "#3a3f3b", topc = c.lit ? TOPF : "#7a827c";
  mk("path", { d: `M${x + fw} ${top}L${x + fw + dx} ${top - dy}L${x + fw + dx} ${base - dy}L${x + fw} ${base}Z`, style: `fill:${side};stroke:none` }, svg);
  mk("rect", { x, y: top, width: fw, height: h, style: `fill:${front};stroke:none` }, svg);
  mk("path", { d: `M${x} ${top}L${x + dx} ${top - dy}L${x + fw + dx} ${top - dy}L${x + fw} ${top}Z`, style: `fill:${topc};stroke:none` }, svg);
  // value and quarter
  const lx = x + fw / 2 + dx / 2;
  if (c.lit) {
    const cr = 19, cy = top - dy / 2 - 30;
    mk("circle", { cx: lx, cy: cy + 5, r: cr, style: `fill:${SIDE}` }, svg);
    mk("circle", { cx: lx, cy, r: cr + 2, style: `fill:${TOPF}` }, svg);
    logoChip(svg, lx, cy, cr - 1, S.logo, S.sym);
    type(svg, lx, cy - cr - 10, c.s, "num", { size: 17, weight: 650, fill: INK, anchor: "middle" });
  } else {
    type(svg, lx, top - dy - 9, c.s, "num", { size: 14, weight: 500, fill: TONE.hi, anchor: "middle" });
  }
  type(svg, x + fw / 2, base + 14, c.label.toUpperCase(), "caps", { fill: c.lit ? INK : TONE.muted, size: 6.4, weight: 750, anchor: "middle" });
});
// the jump between them (only for a rise: on a fall the tall column is last year's)
if (up) {
const a0 = cols[0].x + fw + dx + 10, a1 = cols[1].x - 10, ay = base - hv(S.prev.v) - 30;
mk("path", { d: `M${a0} ${ay}Q${(a0 + a1) / 2} ${ay - 46} ${a1} ${ay - 34}`, class: "nf", style: `stroke:${INK};stroke-width:1.5px;stroke-dasharray:3 3` }, svg);
mk("path", { d: `M${a1 - 8} ${ay - 39}L${a1} ${ay - 34}L${a1 - 7} ${ay - 28}`, class: "nf", style: `stroke:${INK};stroke-width:1.5px` }, svg);
}
grain(0.08);