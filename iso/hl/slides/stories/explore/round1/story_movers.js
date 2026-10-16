// Top movers story, frame 1: the week's biggest gainers and losers as diverging bars, true to scale around one
// zero line. Gainers above in green growing right, losers below in terracotta growing left. IHSG's week is a
// dashed reference line, so each bar reads against the market.
// DATA.slide: { title, up: [{sym, logo, ret, sector}], down: [...], ihsg: {ret}, breadth: {up, down}, universe }
const D = DATA, S = D.slide;
setAccent("buy");
const UP = ACCENTS.buy, DN = ACCENTS.sell;
dotField(0, 0, W, H, { fx: W * 0.75, fy: H * 0.3, reach: 300, op: 0.22 });
const band = storyFrame(D);

const pct = (v, d = 1) => `${v > 0 ? "+" : v < 0 ? "−" : ""}${Math.abs(v * 100).toFixed(d)}%`;

// ---------------------------------------------------------------- headline: the title, then IHSG for context
let y = para(svg, M, band.top + 8, S.title, "title", { size: 21 });
if (S.ihsg) {
  const c = S.ihsg.ret >= 0 ? UP : DN;
  typeRun(svg, M, y + 22, [["IHSG ", 9, 600, TONE.muted], [pct(S.ihsg.ret), 9, 700, c], ["  this week", 9, 500, TONE.muted]]);
}

// ---------------------------------------------------------------- the bars
const rows = [...S.up, ...S.down];
const maxUp = Math.max(...S.up.map((r) => r.ret)), maxDn = Math.max(...S.down.map((r) => -r.ret));
const PAD = 46; // room for the % label past each bar end
const X0 = M + PAD, X1 = W - M - PAD;
const xs = scale(-maxDn, maxUp, X0, X1), zx = xs(0);
const top = y + 46, bottom = band.bottom - 30, gap = 14;
const rh = (bottom - top - gap) / rows.length, bh = Math.min(13, rh * 0.5);
const g = mk("g", {}, svg);

const rowY = (i) => top + i * rh + (i >= S.up.length ? gap : 0) + rh / 2;
rows.forEach((r, i) => {
  const cy = rowY(i), up = r.ret > 0, col = up ? UP : DN, xe = xs(r.ret);
  // faint track across the whole plot, then the bar from zero
  mk("line", { x1: X0, y1: cy, x2: X1, y2: cy, class: "lo thin", style: "stroke-dasharray:1 3" }, g);
  const x = Math.min(zx, xe), w = Math.max(1, Math.abs(xe - zx));
  mk("rect", { x, y: cy - bh / 2, width: w, height: bh, rx: 1.5, style: `fill:${col};fill-opacity:.22;stroke:${col};stroke-width:1px` }, g);
  // the % at the bar's end, the ticker with its logo on the other side of zero
  type(g, up ? xe + 6 : xe - 6, cy + 3.6, pct(r.ret), "label", { fill: col, size: 10.5, weight: 650, anchor: up ? "start" : "end" });
  const lr = 5.4, lx = up ? zx - 6 : zx + 6;
  if (up) {
    type(g, lx - 2 * lr - 4, cy + 3, r.sym, "label", { fill: TONE.hi, size: 8.4, weight: 700, anchor: "end" });
    logoChip(g, lx - lr, cy, lr, r.logo, r.sym);
  } else {
    logoChip(g, lx + lr, cy, lr, r.logo, r.sym);
    type(g, lx + 2 * lr + 4, cy + 3, r.sym, "label", { fill: TONE.hi, size: 8.4, weight: 700 });
  }
});

// zero line, and IHSG's week as a dashed line on the same scale
const y0 = top - 10, y1 = bottom + 4;
mk("line", { x1: zx, y1: y0, x2: zx, y2: y1, style: `stroke:${TONE.edge};stroke-width:1px` }, g);
type(g, zx, y1 + 10, "0", "label", { fill: TONE.faint, size: 6.6, anchor: "middle" });
if (S.ihsg && Math.abs(xs(S.ihsg.ret) - zx) > 2) {
  const ix = xs(S.ihsg.ret);
  mk("line", { x1: ix, y1: y0, x2: ix, y2: y1, class: "dash thin" }, g);
  type(g, ix, y0 - 4, "IHSG", "caps", { fill: TONE.muted, anchor: ix > zx ? "start" : "end" });
}
// group labels in the empty corners
type(g, X1 + PAD, top - 12, "Gainers", "caps", { fill: UP, anchor: "end" });
type(g, X0 - PAD, rowY(S.up.length) - rh / 2 - 2, "Losers", "caps", { fill: DN });

// ---------------------------------------------------------------- breadth, one line
const b = S.breadth;
typeRun(svg, M, band.bottom, [[`${b.up}`, 9, 700, UP], [" rose, ", 9, 500, TONE.muted], [`${b.down}`, 9, 700, DN],
  [` fell of the ${S.universe} largest stocks`, 9, 500, TONE.muted]]);
grain(0.06);
