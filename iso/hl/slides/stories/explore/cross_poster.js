// Crossing 5%, variant A: the breaking-news poster. The ticker huge with its logo, a "new major holder" chip,
// the holder's name, then the jump as two numbers with an arrow between them. No chart.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
glow(W * 0.75, 200, 220, 170, 0.22);
dotField(0, 0, W, H, { fx: W * 0.75, fy: 200, reach: 300, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "OWNERSHIP", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// the ticker, huge, and the logo
logoChip(svg, W - M - 34, y0 + 118, 34, S.logo, S.sym);
type(svg, M - 5, y0 + 148, S.sym, "hero", { size: Math.min(112, (W - 2 * M - 80) / (S.sym.length * 0.64)), weight: 500 });
type(svg, M, y0 + 172, S.name, "label", { fill: TONE.muted, size: 10 });

// chip
const chip = "NEW MAJOR SHAREHOLDER", cw = chip.length * 5.1 + 22;
mk("rect", { x: M, y: y0 + 196, width: cw, height: 18, rx: 9, style: `fill:${FILL};fill-opacity:.18;stroke:${FILL};stroke-width:1px` }, svg);
type(svg, M + cw / 2, y0 + 208.5, chip, "caps", { fill: INK, size: 6.4, weight: 750, anchor: "middle" });

// who
wrapText(S.holder, 26, W - 2 * M, 0.53).forEach((l, i) => type(svg, M, y0 + 254 + i * 30, l, "title", { size: 26, fill: TONE.hi }));
const hy = y0 + 254 + (wrapText(S.holder, 26, W - 2 * M, 0.53).length - 1) * 30;

// the jump
const jy = hy + 92;
type(svg, M, jy, `${S.before.toFixed(2)}%`, "num", { size: 34, weight: 400, fill: TONE.muted });
type(svg, M, jy + 16, "before", "label", { fill: TONE.faint, size: 8 });
mk("path", { d: `M${M + 118} ${jy - 11}H${M + 150}M${M + 143} ${jy - 17}L${M + 150} ${jy - 11}L${M + 143} ${jy - 5}`, class: "nf", style: `stroke:${INK};stroke-width:1.8px` }, svg);
typeRun(svg, M + 166, jy, [[S.now.toFixed(2), 50, 500, INK], ["%", 22, 400, INK]]);
type(svg, M + 168, jy + 16, "now", "label", { fill: INK, size: 8, weight: 650 });

const F = S.facts.map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
