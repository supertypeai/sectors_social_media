// Top broker, isometric podium: the top 5 brokers as solid iso columns, heights true to value traded, #1 in the
// centre (order 4·2·1·3·5). Each column wears its logo as a thick 3D coin on top, its % share above, and its code,
// value and a bought/sold split on the front face.
const D = DATA, R = D.rows.slice(0, 5);
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
glow(W / 2, 330, 220, 200, 0.2);
dotField(0, 0, W, H, { fx: W / 2, fy: 420, reach: 300, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company.toUpperCase(), "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 46, "TOP 5", "hero", { size: 44, weight: 800, fill: GI });
type(svg, M, y0 + 80, D.title || (D.period === "day" ? "Brokers today" : "Brokers this week"), "hero", { size: 26, weight: 600 });
type(svg, M, y0 + 98, `By value traded · ${D.market} on the IDX`, "label", { fill: TONE.muted, size: 8.5 });

// geometry: front face width, iso depth offset (dx up-right, dy up)
const order = [3, 1, 0, 2, 4], n = order.length, fw = 50, gap = 8, dx = 14, dy = 8;
const totalW = n * fw + (n - 1) * gap + dx, x0 = (W - totalW) / 2, base = SAFE.bottom - 52;
// as tall as the room under the title allows (minus the coin and tag on top); heights stay true to value
const maxH = base - (y0 + 108) - 66;
const fmt = (v) => (v >= 1e12 ? `${(v / 1e12).toFixed(1)} T` : `${Math.round(v / 1e9)} B`);
// draw back to front so nothing overlaps wrongly: left to right is fine for this view
order.forEach((ri, k) => {
  const r = R[ri], h = maxH * (r.gross / R[0].gross), x = x0 + k * (fw + gap), top = base - h, first = ri === 0;
  // the column IS the split: bought (green) at the bottom, sold (terracotta) stacked on top, true to value
  const pb = r.buy / (r.buy + r.sell), hb = h * pb, mid = base - hb;
  const face = (y1, y2, front, side) => {
    mk("path", { d: `M${x + fw} ${y1}L${x + fw + dx} ${y1 - dy}L${x + fw + dx} ${y2 - dy}L${x + fw} ${y2}Z`, style: `fill:${side};stroke:none` }, svg);
    mk("rect", { x, y: y1, width: fw, height: y2 - y1, style: `fill:${front};stroke:none` }, svg);
  };
  face(mid, base, G, "#5f7d66");
  face(top, mid, T, "#8f5444");
  mk("line", { x1: x, y1: mid, x2: x + fw, y2: mid, style: `stroke:${TONE.ground};stroke-width:1.2px` }, svg);
  mk("path", { d: `M${x + fw} ${mid}L${x + fw + dx} ${mid - dy}`, style: `stroke:${TONE.ground};stroke-width:1.2px` }, svg);
  mk("path", { d: `M${x} ${top}L${x + dx} ${top - dy}L${x + fw + dx} ${top - dy}L${x + fw} ${top}Z`, style: `fill:#d9a090;stroke:none` }, svg);
  if (first) mk("path", { d: `M${x} ${base}V${top}L${x + dx} ${top - dy}H${x + fw + dx}V${base - dy}L${x + fw} ${base}Z`, class: "nf", style: `stroke:${TONE.hi};stroke-width:1.2px` }, svg);
  // rank, code, value in the sold part; bought / sold amounts in their own segments
  // a short sold block gets rank and code on one line so its "Sold" label always fits
  if (mid - top > 54) {
    type(svg, x + fw / 2, top + 20, String(ri + 1), "num", { size: 20, weight: 700, fill: TONE.ground, anchor: "middle" });
    type(svg, x + fw / 2, top + 34, r.code, "label", { fill: TONE.ground, size: 10, weight: 800, anchor: "middle" });
  } else {
    typeRun(svg, x + fw / 2, top + 17, [[String(ri + 1), 15, 700, TONE.ground], [` ${r.code}`, 9.5, 800, TONE.ground]], { anchor: "middle" });
  }
  type(svg, x + fw / 2, mid - 6, `Sold ${fmt(r.sell)}`, "label", { fill: TONE.ground, size: 6.4, weight: 700, anchor: "middle" });
  type(svg, x + fw / 2, base - 8, `Bought ${fmt(r.buy)}`, "label", { fill: TONE.ground, size: 6.4, weight: 700, anchor: "middle" });
  const lean = r.net >= 0;
  type(svg, x + fw / 2, base + 13, `Net ${lean ? "Buy" : "Sell"}`, "label", { fill: lean ? GI : TI, size: 7.2, weight: 750, anchor: "middle" });
  type(svg, x + fw / 2, base + 23, r.net_s.replace("Rp ", ""), "label", { fill: lean ? GI : TI, size: 6.6, anchor: "middle" });

  // the coin: a thick disc standing on the top face
  const cx = x + fw / 2 + dx / 2, cy = top - dy / 2 - 22, cr = 17, th = 5;
  mk("ellipse", { cx, cy: cy + th, rx: cr, ry: cr, style: `fill:${first ? "#6f8f76" : "#4a524c"};stroke:none` }, svg);
  mk("rect", { x: cx - cr, y: cy, width: 2 * cr, height: th, style: `fill:${first ? "#6f8f76" : "#4a524c"};stroke:none` }, svg);
  mk("circle", { cx, cy, r: cr + 1.5, style: `fill:${first ? GI : "#9aa59c"};stroke:none` }, svg);
  logoChip(svg, cx, cy, cr - 1.5, r.logo, r.code);
  // % share label above the coin
  const lab = `${r.share.toFixed(1)}%`, lw = lab.length * 6 + 12;
  mk("rect", { x: cx - lw / 2, y: cy - cr - 22, width: lw, height: 15, rx: 4, style: `fill:${TONE.ground};fill-opacity:.85;stroke:${first ? GI : TONE.mid};stroke-width:.8px` }, svg);
  type(svg, cx, cy - cr - 11, lab, "label", { fill: first ? GI : TONE.hi, size: 9, weight: 750, anchor: "middle" });
});
// floor
mk("path", { d: `M${x0 - 10} ${base}L${x0 + totalW + 4} ${base}L${x0 + totalW + 4 + dx} ${base - dy}`, class: "nf", style: `stroke:${TONE.mid};stroke-width:1px` }, svg);

typeRun(svg, M, SAFE.bottom - 4, [["% = share of all broker value  ·  ", 8.4, 600, TONE.hi], ["Bought", 8.4, 700, GI], [" / ", 8.4, 500, TONE.muted], ["Sold", 8.4, 700, TI]]);
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
