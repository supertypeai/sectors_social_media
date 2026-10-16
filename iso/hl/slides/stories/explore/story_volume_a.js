// Volume spike story, direction A: number-led. The multiple is the hero, set huge in the accent ink across
// the frame; the company sits above it; the month of volume runs as solid bars along the bottom, the spike
// the one bar in the accent. One fact, one proof.
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159"; // Foundations --primary-ink / --secondary-ink

dotField(0, 0, W, H, { fx: W * 0.7, fy: 240, reach: 340, op: 0.32 });
glow(W * 0.62, 250, 230, 170, 0.22);

// top: kicker and date, inside the safe area
const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// the company: a big logo and the ticker
logoChip(svg, M + 20, y0 + 44, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 44, L.sym, "hero", { size: 30, weight: 650 });
type(svg, M + 50, y0 + 58, L.name, "label", { fill: TONE.muted, size: 8.5 });

// the hero: the multiple
typeRun(svg, M - 6, y0 + 232, [[L.ratioTxt, 190, 500, INK], ["×", 80, 400, INK]]);
type(svg, M, y0 + 268, "a normal day's volume", "title", { fill: TONE.hi });
type(svg, M, y0 + 288, `${L.volumeTxt} shares traded · a normal day is ${L.medianTxt}`, "label", { fill: TONE.muted, size: 9 });

// the month, as solid bars across the bottom; the last bar is the spike
const bars = L.bars, B = { x0: M, x1: W - M, y0: y0 + 318, y1: SAFE.bottom - 46 };
const max = Math.max(...bars.map((b) => b.v)), bw = (B.x1 - B.x0) / bars.length;
const ys = scale(0, max, B.y1, B.y0);
bars.forEach((b, i) => {
  const last = i === bars.length - 1, x = B.x0 + i * bw + 1, top = ys(b.v);
  mk("rect", { x, y: top, width: bw - 2, height: B.y1 - top, rx: 1.2, style: `fill:${last ? FILL : TONE.mid};stroke:none` }, svg);
});
const my = ys(L.median);
mk("line", { x1: B.x0, y1: my, x2: B.x1, y2: my, style: `stroke:${TONE.hi};stroke-width:.8px;stroke-dasharray:2 3;opacity:.7` }, svg);
type(svg, B.x0, my - 4, "normal day", "label", { fill: TONE.hi, size: 6.6 });
type(svg, B.x1, B.y1 + 12, "today", "label", { fill: INK, size: 7, weight: 650, anchor: "end" });
type(svg, B.x0, B.y1 + 12, "30 days ago", "label", { fill: TONE.faint, size: 7 });

// one fact, then the source
type(svg, M, SAFE.bottom - 14, `Price ${L.chgTxt} that day · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 14, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
