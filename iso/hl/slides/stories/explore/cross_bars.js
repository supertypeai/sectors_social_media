// Crossing 5%, Voronoi-style: the month's new major shareholders as bars growing from the left edge, true to
// their stake; the company logo sits large at each bar's end, the holder and stake beside it. A dashed 5% line
// runs through all of them. Title block in the empty corner.
const D = DATA, R = D.rows.slice(0, 6);
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company.toUpperCase(), "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

const TOP = y0 + 140, BOT = SAFE.bottom - 40, RH = Math.min(62, (BOT - TOP) / R.length), bh = RH * 0.6;
// title block on top
type(svg, M, y0 + 48, "New 5%", "hero", { size: 38, weight: 500 });
type(svg, M, y0 + 88, "owners", "hero", { size: 38, weight: 500, fill: INK });
type(svg, M, y0 + 108, "Ranked by stake now · last 30 days", "label", { fill: TONE.muted, size: 9 });
const max = Math.max(...R.map((r) => r.now)), x1 = W - M - 30, xs = scale(0, max, 0, x1);
// bars
R.forEach((r, i) => {
  const cy = TOP + i * RH + RH / 2, len = xs(r.now), b0 = xs(r.before);
  mk("rect", { x: -6, y: cy - bh / 2, width: len + 6, height: bh, rx: bh / 2, style: `fill:${FILL};fill-opacity:${0.55 + 0.4 * (r.now / max)};stroke:none` }, svg);
  if (r.before > 0) mk("rect", { x: -6, y: cy - bh / 2, width: b0 + 6, height: bh, rx: bh / 2, style: `fill:${TONE.ground};fill-opacity:.45;stroke:none` }, svg);
  // logo at the end, sized to the bar
  const lr = Math.min(bh / 2 + 3, 20), lx = Math.max(len, M + lr);
  logoChip(svg, lx, cy, lr, r.logo, r.sym);
  // the words: inside the bar when it's long, else right after the logo
  const inside = len > 230, tx = inside ? M : lx + lr + 7, fg = inside ? TONE.ground : TONE.hi;
  type(svg, tx, cy - 3, r.sym, "label", { fill: fg, size: 12, weight: 800 });
  type(svg, tx, cy + 8, r.holder, "label", { fill: inside ? TONE.ground : TONE.muted, size: 7, weight: 600 });
  const sx = inside ? lx - lr - 8 : W - M, anc = "end";
  if (inside || lx + lr + 7 + r.holder.length * 3.6 < W - M - 60) {
    type(svg, sx, cy + 1, `${r.now.toFixed(2)}%`, "num", { size: 17, weight: 600, fill: inside ? TONE.ground : INK, anchor: anc });
    type(svg, sx, cy + 12, r.before ? `from ${r.before.toFixed(2)}%` : "new holder", "label", { fill: inside ? TONE.ground : TONE.muted, size: 6.8, anchor: anc });
  }
});
// the 5% line
const f5 = xs(5);
const lastY = TOP + R.length * RH;
mk("line", { x1: f5, y1: TOP - 10, x2: f5, y2: lastY, style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:3 3;opacity:.6` }, svg);
type(svg, f5 + 4, TOP - 4, "5% line", "label", { fill: TONE.hi, size: 7, weight: 700 });


type(svg, M, SAFE.bottom - 4, "Owning 5% or more makes you a major shareholder", "label", { fill: TONE.hi, size: 8.6, weight: 600 });
grain(0.09);
