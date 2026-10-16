// Crossing 5%, "through the glass": two iso columns, the holder's stake BEFORE and NOW, standing on a floor, with
// a translucent glass plane at the 5% level. The before column stops under the plane; the now column breaks
// through it, its part above the plane in green. The logo rides on top of the now column as a 3D coin.
const D = DATA, S = D.s;
setAccent("buy");
const G = "#81a789", GI = "#b2d2b9";
glow(W * 0.62, 330, 220, 200, 0.2);
dotField(0, 0, W, H, { fx: W / 2, fy: 440, reach: 300, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day.toUpperCase(), "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// headline: who, crossed what
wrapText(S.holder, 24, W - 2 * M, 0.52).slice(0, 2).forEach((l, i) => type(svg, M, y0 + 42 + i * 27, l, "title", { size: 24, fill: TONE.hi }));
const hl = Math.min(2, wrapText(S.holder, 24, W - 2 * M, 0.52).length);
typeRun(svg, M, y0 + 42 + hl * 27 + 2, [["broke through ", 15, 500, TONE.muted], ["5%", 15, 800, GI], [" of ", 15, 500, TONE.muted], [S.sym, 15, 800, TONE.hi]]);

// iso geometry
const base = SAFE.bottom - 70, maxV = Math.max(12, S.now * 1.15), Hmax = base - (y0 + 150), hv = (v) => Hmax * (v / maxV);
const fw = 74, dx = 26, dy = 15;
const cols = [{ v: S.before, x: M + 22, label: "BEFORE", sub: "" }, { v: S.now, x: W - M - fw - dx - 18, label: "NOW", sub: S.day }];
const plane = base - hv(5);

function column(c, now) {
  const top = base - hv(c.v), x = c.x;
  const seg = (y1, y2, front, side) => {
    if (y2 <= y1) return;
    mk("path", { d: `M${x + fw} ${y1}L${x + fw + dx} ${y1 - dy}L${x + fw + dx} ${y2 - dy}L${x + fw} ${y2}Z`, style: `fill:${side};stroke:none` }, svg);
    mk("rect", { x, y: y1, width: fw, height: y2 - y1, style: `fill:${front};stroke:none` }, svg);
  };
  if (now) { seg(Math.max(top, plane), base, "#6c746e", "#4b524d"); seg(top, plane, G, "#5f7d66"); }
  else seg(top, base, "#6c746e", "#4b524d");
  mk("path", { d: `M${x} ${top}L${x + dx} ${top - dy}L${x + fw + dx} ${top - dy}L${x + fw} ${top}Z`, style: `fill:${now ? "#c5dccb" : "#9aa29c"};stroke:none` }, svg);
  return top;
}

// back half of the glass plane (drawn before columns), columns, front edge of the plane (after)
const px0 = M - 6, px1 = W - M - 4, pDepth = 34;
mk("path", { d: `M${px0} ${plane}L${px0 + dx * 1.3} ${plane - pDepth * 0.6}L${px1 + dx * 0.3} ${plane - pDepth * 0.6}L${px1} ${plane}Z`, style: `fill:${GI};fill-opacity:.1;stroke:${GI};stroke-opacity:.5;stroke-width:.8px` }, svg);
const tB = column(cols[0], false), tN = column(cols[1], true);
mk("line", { x1: px0, y1: plane, x2: px1, y2: plane, style: `stroke:${GI};stroke-width:1.2px;stroke-dasharray:4 3` }, svg);
type(svg, px0 + 6, plane - 8, "5% · MAJOR SHAREHOLDER LINE", "caps", { fill: GI, size: 5.8, weight: 750 });

// values on the columns
type(svg, cols[0].x + fw / 2, tB - dy - 10, `${S.before.toFixed(2)}%`, "num", { size: 20, weight: 500, fill: TONE.hi, anchor: "middle" });
// the coin on the now column
const ccx = cols[1].x + fw / 2 + dx / 2, ccy = tN - dy / 2 - 26, cr = 22;
mk("ellipse", { cx: ccx, cy: ccy + 6, rx: cr, ry: cr, style: "fill:#5f7d66" }, svg);
mk("rect", { x: ccx - cr, y: ccy, width: 2 * cr, height: 6, style: "fill:#5f7d66" }, svg);
mk("circle", { cx: ccx, cy: ccy, r: cr + 2, style: `fill:${GI}` }, svg);
logoChip(svg, ccx, ccy, cr - 1, S.logo, S.sym);
typeRun(svg, ccx, ccy - cr - 14, [[S.now.toFixed(2), 30, 600, GI], ["%", 14, 500, GI]], { anchor: "middle" });

// labels under the floor
mk("line", { x1: M - 6, y1: base, x2: W - M, y2: base, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
cols.forEach((c, i) => {
  type(svg, c.x + fw / 2, base + 16, c.label, "caps", { fill: i ? GI : TONE.muted, size: 6.6, weight: 750, anchor: "middle" });
});
// the jump, between the columns
const ax0 = cols[0].x + fw + dx + 8, ax1 = cols[1].x - 8, ay = (tB + tN) / 2 - 10;
mk("path", { d: `M${ax0} ${ay + 20}Q${(ax0 + ax1) / 2} ${ay - 30} ${ax1} ${ay}`, class: "nf", style: `stroke:${GI};stroke-width:1.6px;stroke-dasharray:3 3` }, svg);
mk("path", { d: `M${ax1 - 7} ${ay - 5}L${ax1} ${ay}L${ax1 - 8} ${ay + 4}`, class: "nf", style: `stroke:${GI};stroke-width:1.6px` }, svg);
type(svg, (ax0 + ax1) / 2, ay - 20, `+${(S.now - S.before).toFixed(2)} pts`, "label", { fill: GI, size: 10, weight: 750, anchor: "middle" });

const F = S.facts.map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
