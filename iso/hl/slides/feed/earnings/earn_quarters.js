// Earnings, slide 2: the last six quarters of profit as solid bars, so the jump is seen in its trend. This
// quarter in the accent, the same quarter last year outlined, the rest grey; values on the bars.
// DATA.slide: { title, sym, logo, bars: [{label, v, s, hi, pair}] }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
para(svg, M, 74, S.title, "title");
type(svg, M, 92, "Net profit each quarter", "body", { fill: TONE.muted, size: 8.5 });

const B = { x0: M, x1: W - M, y0: 130, y1: H - 70 }, n = S.bars.length, bw = (B.x1 - B.x0) / n;
const vmax = Math.max(...S.bars.map((b) => b.v)), vmin = Math.min(0, ...S.bars.map((b) => b.v));
const ys = scale(vmin, vmax * 1.12, B.y1, B.y0), z = ys(0);
mk("line", { x1: B.x0, y1: z, x2: B.x1, y2: z, style: `stroke:${TONE.edge};stroke-width:.8px` }, svg);
S.bars.forEach((b, i) => {
  const x = B.x0 + i * bw + 6, w = bw - 12, y = Math.min(ys(b.v), z), h = Math.abs(ys(b.v) - z);
  const style = b.hi ? `fill:${FILL};stroke:none` : b.pair ? `fill:none;stroke:${INK};stroke-width:1.2px;stroke-dasharray:3 2` : `fill:${TONE.mid};stroke:none`;
  mk("rect", { x, y, width: w, height: Math.max(1.5, h), rx: 3, style }, svg);
  type(svg, x + w / 2, (b.v >= 0 ? y : y + h) + (b.v >= 0 ? -6 : 14), b.s.replace("Rp ", ""), "label", { fill: b.hi ? INK : TONE.muted, size: b.hi ? 9 : 7.4, weight: b.hi ? 750 : 500, anchor: "middle" });
  type(svg, x + w / 2, B.y1 + 14, b.label, "label", { fill: b.hi ? INK : TONE.faint, size: 7, weight: b.hi ? 700 : 500, anchor: "middle" });
});
const pi = S.bars.findIndex((b) => b.pair), hi = S.bars.findIndex((b) => b.hi);
if (pi >= 0) type(svg, M, H - 46, "Dashed = the same quarter last year", "label", { fill: TONE.muted, size: 7.6 });
grain(0.08);
