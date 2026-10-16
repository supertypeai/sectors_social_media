// Crossing 5%, direction 3: the new seat at the table. The company as a 100-square grid (1 square = 1%), each
// major holder a block of squares, the newcomer in green, everyone else faint. Who owns what at one glance.
const D = DATA, S = D.s, O = D.owners;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 40, 20, S.logo, S.sym);
type(svg, M + 50, y0 + 45, S.sym, "hero", { size: 32, weight: 650 });
type(svg, M + 50, y0 + 59, S.name, "label", { fill: TONE.muted, size: 8.5 });

type(svg, M, y0 + 100, `A new holder owns`, "label", { fill: TONE.hi, size: 11, weight: 600 });
typeRun(svg, M - 2, y0 + 142, [[`${S.now.toFixed(2)}%`, 40, 500, INK], [` of ${S.sym}`, 18, 500, TONE.hi]]);

// the grid: 10 × 10, filled holder by holder (biggest first, the newcomer in its rank), then everyone else
// the grid is sized to leave room for the legend (holders + "everyone else") above the footer
const legendH = (O.length + 1) * 14 + 22;
const size = Math.min((W - 2 * M) / 10, (SAFE.bottom - 24 - legendH - (y0 + 166)) / 10), gap = 2.4;
const g0 = { x: (W - 10 * size) / 2, y: y0 + 166 };
const greys = [0.32, 0.2, 0.13, 0.09];
let k = 0, gi = 0;
const blocks = O.map((o) => ({ ...o, n: Math.round(o.pct), tone: o.mover ? FILL : TONE.hi, op: o.mover ? 1 : greys[gi++] ?? 0.08 }));
for (const b of blocks) {
  b.first = k;
  for (let i = 0; i < b.n && k < 100; i++, k++) {
    const c = k % 10, r = Math.floor(k / 10);
    mk("rect", { x: g0.x + c * size + gap / 2, y: g0.y + r * size + gap / 2, width: size - gap, height: size - gap, rx: 3,
      style: `fill:${b.tone};fill-opacity:${b.op};stroke:none` }, svg);
  }
}
for (; k < 100; k++) {
  const c = k % 10, r = Math.floor(k / 10);
  mk("rect", { x: g0.x + c * size + gap / 2, y: g0.y + r * size + gap / 2, width: size - gap, height: size - gap, rx: 3,
    style: `fill:none;stroke:${TONE.mid};stroke-width:.8px` }, svg);
}
// legend
let ly = g0.y + 10 * size + 18;
blocks.forEach((b) => {
  mk("rect", { x: M, y: ly - 7, width: 8, height: 8, rx: 2, style: `fill:${b.tone};fill-opacity:${b.op};stroke:none` }, svg);
  type(svg, M + 14, ly, b.mover ? `${b.name}  · new` : b.name.replace(/^PT /, ""), "label", { fill: b.mover ? INK : TONE.hi, size: 8.4, weight: b.mover ? 700 : 500 });
  type(svg, W - M, ly, `${b.pct.toFixed(2)}%`, "label", { fill: b.mover ? INK : TONE.hi, size: 8.4, weight: 650, anchor: "end" });
  ly += 14;
});
mk("rect", { x: M, y: ly - 7, width: 8, height: 8, rx: 2, style: `fill:none;stroke:${TONE.mid};stroke-width:.8px` }, svg);
type(svg, M + 14, ly, "Everyone else", "label", { fill: TONE.muted, size: 8.4 });

type(svg, M, SAFE.bottom - 4, "1 square = 1% of the company", "label", { fill: TONE.hi, size: 8.6, weight: 600 });
grain(0.09);
