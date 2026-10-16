// Crossing 5%, direction 1: the meter. A tall ownership bar (0–15%) fills from the old stake to the new one,
// through a dashed 5% "major shareholder" line. The new stake is the hero.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
dotField(0, 0, W, H, { fx: W * 0.7, fy: 330, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 40, 20, S.logo, S.sym);
type(svg, M + 50, y0 + 45, S.sym, "hero", { size: 32, weight: 650 });
type(svg, M + 50, y0 + 59, S.name, "label", { fill: TONE.muted, size: 8.5 });

// left: the words and the number
type(svg, M, y0 + 108, S.holder, "label", { fill: TONE.hi, size: 15, weight: 650 });
type(svg, M, y0 + 124, "now owns", "label", { fill: TONE.muted, size: 10 });
typeRun(svg, M - 3, y0 + 196, [[S.now.toFixed(2), 64, 500, INK], ["%", 26, 400, INK]]);
type(svg, M, y0 + 218, `up from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 10 });
const F = S.facts;
F.forEach((f, i) => {
  type(svg, M, y0 + 268 + i * 38, f.value, "num", { size: 18, weight: 450, fill: TONE.hi });
  type(svg, M, y0 + 281 + i * 38, f.label, "label", { fill: TONE.muted, size: 7.6 });
});

// right: the meter
const mx = W - M - 70, mw = 56, top = y0 + 92, bot = SAFE.bottom - 40, max = 15;
const ys = scale(0, max, bot, top);
mk("rect", { x: mx, y: top, width: mw, height: bot - top, rx: 10, style: `fill:${TONE.card};stroke:${TONE.mid};stroke-width:1px` }, svg);
mk("rect", { x: mx + 4, y: ys(S.before), width: mw - 8, height: bot - 4 - ys(S.before), rx: 6, style: `fill:${TONE.hi};fill-opacity:.18;stroke:none` }, svg);
mk("rect", { x: mx + 4, y: ys(S.now), width: mw - 8, height: ys(S.before) - ys(S.now), rx: 6, style: `fill:${FILL};stroke:none` }, svg);
glow(mx + mw / 2, ys(S.now), 70, 40, 0.25);
const fy = ys(5);
mk("line", { x1: mx - 16, y1: fy, x2: mx + mw + 6, y2: fy, style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:3 3` }, svg);
type(svg, mx - 18, fy - 3, "5%", "label", { fill: TONE.hi, size: 9, weight: 700, anchor: "end" });
type(svg, mx - 18, fy + 8, "major holder", "label", { fill: TONE.muted, size: 6.6, anchor: "end" });
[0, 10, 15].forEach((v) => type(svg, mx + mw + 6, ys(v) + 3, `${v}%`, "label", { fill: TONE.faint, size: 6.6 }));
type(svg, mx + mw / 2, ys(S.now) - 8, `${S.now.toFixed(2)}%`, "label", { fill: INK, size: 9, weight: 700, anchor: "middle" });

type(svg, M, SAFE.bottom - 4, "Owning 5% or more makes you a major shareholder", "label", { fill: TONE.hi, size: 8.6, weight: 600 });
grain(0.09);
