// Crossing 5%, simple: one sentence, one number, one bar. The stake as a single horizontal bar from 0 to 15%,
// the old part grey, the new part green, a short tick at 5%. Three facts in one line. Nothing else.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
glow(W * 0.5, 330, 220, 160, 0.16);

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// the company
logoChip(svg, M + 24, y0 + 54, 24, S.logo, S.sym);
type(svg, M + 58, y0 + 60, S.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 58, y0 + 75, S.name, "label", { fill: TONE.muted, size: 9 });

// the sentence
const lines = wrapText(`${S.holder} now owns`, 22, W - 2 * M, 0.52);
lines.forEach((l, i) => type(svg, M, y0 + 170 + i * 26, l, "title", { size: 22, fill: TONE.hi }));
const ny = y0 + 170 + lines.length * 26 + 84;

// the number
typeRun(svg, M - 4, ny, [[S.now.toFixed(2), 88, 500, INK], ["%", 34, 400, INK]]);
type(svg, M, ny + 26, `of ${S.sym}, up from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 11 });

// the bar: 0 → 15%
const bx0 = M, bx1 = W - M, by = ny + 86, bh = 14, xs = scale(0, 15, bx0, bx1);
mk("rect", { x: bx0, y: by, width: bx1 - bx0, height: bh, rx: bh / 2, style: `fill:${TONE.card};stroke:none` }, svg);
mk("rect", { x: bx0, y: by, width: xs(S.before) - bx0, height: bh, rx: bh / 2, style: `fill:${TONE.hi};fill-opacity:.35;stroke:none` }, svg);
mk("rect", { x: xs(S.before) + 1.5, y: by, width: xs(S.now) - xs(S.before) - 1.5, height: bh, rx: 3, style: `fill:${FILL};stroke:none` }, svg);
const f5 = xs(5);
mk("line", { x1: f5, y1: by - 7, x2: f5, y2: by + bh + 7, style: `stroke:${TONE.hi};stroke-width:1.4px` }, svg);
type(svg, f5, by + bh + 19, "5% = major shareholder", "label", { fill: TONE.hi, size: 8, weight: 600, anchor: "middle" });
type(svg, bx0, by - 8, "0%", "label", { fill: TONE.faint, size: 7.4 });
type(svg, bx1, by - 8, "15%", "label", { fill: TONE.faint, size: 7.4, anchor: "end" });

// one line of facts
const F = S.facts.map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
