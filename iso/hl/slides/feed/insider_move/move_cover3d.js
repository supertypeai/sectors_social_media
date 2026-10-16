// Insider move, slide 1 (the hook): the question, then the holder's stake BEFORE and NOW as two iso columns
// (true to scale). On a sale the NOW column keeps a dashed ghost of what it was, the sold slab in the accent;
// on a buy the added slab is the accent. The company logo rides the moved column as a 3D coin.
// DATA.slide: { sym, name, logo, question, accent[], holder, moved, before, after, value, day, buy }
const D = DATA, S = D.slide, buy = S.buy;
setAccent(D.direction);
const FILL = buy ? "#81a789" : "#c07159", INK = buy ? "#b2d2b9" : "#dc8d74", SIDE = buy ? "#5f7d66" : "#8f5444", TOPF = buy ? "#c5dccb" : "#e9b9a9";
dotField(0, 0, W, H, { fx: W * 0.65, fy: 360, reach: 280, op: 0.3 });
frame(D);

// the question
const ql = wrapText(S.question, 21, W - 2 * M, 0.5).slice(0, 3);
ql.forEach((l, i) => {
  const t = type(svg, M, 74 + i * 24, "", "title", { size: 21 });
  t.innerHTML = l.split(" ").map((w) => (S.accent ?? []).includes(w.replace(/[?,.]/g, "")) || (S.accent ?? []).some((a) => w.startsWith(a))
    ? `<tspan style="fill:${INK}">${w.replace(/&/g, "&amp;")}</tspan>` : w.replace(/&/g, "&amp;")).join(" ");
});
const qb = 74 + (ql.length - 1) * 24;

// columns
const base = H - 92, top0 = qb + 98, maxH = base - top0, fw = 64, dx = 22, dy = 13;
const vmax = Math.max(S.before, S.after), hv = (v) => Math.max(4, maxH * (v / vmax));
const xs = [M + 36, W - M - fw - dx - 40];
const block = (x, y1, y2, front, side, topc, dash) => {
  if (y2 - y1 < 0.5) return;
  if (dash) {
    const st = `fill:none;stroke:${INK};stroke-width:1.1px;stroke-dasharray:3 3`;
    mk("path", { d: `M${x} ${y2}V${y1}L${x + dx} ${y1 - dy}H${x + fw + dx}V${y2 - dy}L${x + fw} ${y2}ZM${x} ${y1}H${x + fw}L${x + fw + dx} ${y1 - dy}M${x + fw} ${y1}V${y2}`, style: st }, svg);
    return;
  }
  mk("path", { d: `M${x + fw} ${y1}L${x + fw + dx} ${y1 - dy}L${x + fw + dx} ${y2 - dy}L${x + fw} ${y2}Z`, style: `fill:${side};stroke:none` }, svg);
  mk("rect", { x, y: y1, width: fw, height: y2 - y1, style: `fill:${front};stroke:none` }, svg);
  mk("path", { d: `M${x} ${y1}L${x + dx} ${y1 - dy}L${x + fw + dx} ${y1 - dy}L${x + fw} ${y1}Z`, style: `fill:${topc};stroke:none` }, svg);
};
mk("path", { d: `M${M - 6} ${base}L${W - M} ${base}`, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
// BEFORE
const tb = base - hv(S.before);
block(xs[0], tb, base, "#4f5550", "#3a3f3b", "#7a827c");
type(svg, xs[0] + fw / 2 + dx / 2, tb - dy - 8, `${S.before.toFixed(2)}%`, "num", { size: 15, weight: 500, fill: TONE.hi, anchor: "middle" });
// NOW: kept part grey, the moved slab in the accent (a ghost when sold)
const x = xs[1], ta = base - hv(S.after);
if (buy) {
  const tKeep = base - hv(S.before);
  block(x, tKeep, base, "#4f5550", "#3a3f3b", "#7a827c");
  block(x, ta, tKeep, FILL, SIDE, TOPF);
} else {
  block(x, ta, base, "#4f5550", "#3a3f3b", "#7a827c");
  block(x, tb, ta, null, null, null, true);
}
const topMost = Math.min(ta, tb), cx = x + fw / 2 + dx / 2;
// the moved slab label, inside it
const slabTop = buy ? ta : tb, slabBot = buy ? base - hv(S.before) : ta;
if (slabBot - slabTop > 22) {
  type(svg, x + fw / 2, (slabTop + slabBot) / 2 + 4, `${buy ? "+" : "−"}${S.moved.toFixed(1)}%`, "label", { fill: buy ? TONE.ground : INK, size: 11, weight: 800, anchor: "middle" });
}
// coin + now value
const cr = 18, cy = topMost - dy / 2 - 28;
mk("circle", { cx, cy: cy + 5, r: cr, style: `fill:${SIDE}` }, svg);
mk("circle", { cx, cy, r: cr + 2, style: `fill:${TOPF}` }, svg);
logoChip(svg, cx, cy, cr - 1, S.logo, S.sym);
type(svg, cx, cy - cr - 10, `${S.after.toFixed(2)}%`, "num", { size: 17, weight: 650, fill: INK, anchor: "middle" });
// floor labels
type(svg, xs[0] + fw / 2, base + 14, "BEFORE", "caps", { fill: TONE.muted, size: 6.4, weight: 750, anchor: "middle" });
type(svg, x + fw / 2, base + 14, `NOW · ${S.day.toUpperCase()}`, "caps", { fill: INK, size: 6.4, weight: 750, anchor: "middle" });

// stats strip
const Y = H - 52, cw = (W - 2 * M) / 3;
mk("line", { x1: M, y1: Y - 14, x2: W - M, y2: Y - 14, class: "lo thin" }, svg);
[["HOLDER", S.holder], [buy ? "BOUGHT" : "SOLD", `${S.moved.toFixed(2)}% of ${S.sym}`], ["VALUE", S.value]].forEach(([k, v], i) => {
  type(svg, M + i * cw, Y - 3, k, "caps", { fill: TONE.faint, size: 5.4 });
  const vv = v.length > 22 ? v.split(" ").slice(0, 2).join(" ") : v;
  type(svg, M + i * cw, Y + 9, vv, "label", { fill: i === 2 ? INK : TONE.hi, size: 8.4, weight: 650 });
});
grain(0.08);
