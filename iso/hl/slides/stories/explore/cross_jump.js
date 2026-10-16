// Crossing 5%, direction 4: the jump. The holder's name big, then one number line from 0% to 15% with the
// 5% mark: the old stake a grey dot left of it, the new stake a green dot right of it, an arc leaping over the line.
const D = DATA, S = D.s;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
dotField(0, 0, W, H, { fx: W / 2, fy: 330, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

const hl = wrapText(S.holder, 32, W - 2 * M, 0.55);
hl.forEach((l, i) => type(svg, M - 1, y0 + 50 + i * 36, l, "hero", { size: 32, weight: 600 }));
const hy = y0 + 50 + (hl.length - 1) * 36;
logoChip(svg, M + 13, hy + 34, 13, S.logo, S.sym);
typeRun(svg, M + 32, hy + 38, [["crossed 5% of ", 13, 500, TONE.muted], [S.sym, 13, 750, TONE.hi]]);

// the number line
const L = { x0: M + 4, x1: W - M - 4, y: hy + 200 }, xs = scale(0, 15, L.x0, L.x1);
mk("line", { x1: L.x0, y1: L.y, x2: L.x1, y2: L.y, style: `stroke:${TONE.mid};stroke-width:2px;stroke-linecap:round` }, svg);
for (let v = 0; v <= 15; v++) mk("line", { x1: xs(v), y1: L.y - (v % 5 ? 3 : 6), x2: xs(v), y2: L.y + (v % 5 ? 3 : 6), style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
[0, 10, 15].forEach((v) => type(svg, xs(v), L.y + 20, `${v}%`, "label", { fill: TONE.faint, size: 7.4, anchor: "middle" }));
// the 5% line
const fx = xs(5);
mk("line", { x1: fx, y1: L.y - 120, x2: fx, y2: L.y + 8, style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:3 3` }, svg);
type(svg, fx, L.y + 20, "5%", "label", { fill: TONE.hi, size: 9, weight: 700, anchor: "middle" });
type(svg, fx + 5, L.y - 110, "major shareholder line", "label", { fill: TONE.muted, size: 7 });
// the leap
const a = xs(S.before), b = xs(S.now), peak = L.y - 104;
mk("path", { d: `M${a} ${L.y}C${a} ${peak} ${b} ${peak} ${b} ${L.y}`, class: "nf", style: `stroke:${FILL};stroke-width:2px;stroke-dasharray:4 3` }, svg);
mk("circle", { cx: a, cy: L.y, r: 6, style: `fill:${TONE.ground};stroke:${TONE.hi};stroke-width:1.5px` }, svg);
glowDot(svg, b, L.y, FILL, 7);
type(svg, a, L.y + 38, `${S.before.toFixed(2)}%`, "num", { size: 16, weight: 400, fill: TONE.muted, anchor: "middle" });
type(svg, a, L.y + 50, "before", "label", { fill: TONE.faint, size: 7, anchor: "middle" });
typeRun(svg, b, L.y + 46, [[S.now.toFixed(2), 34, 500, INK], ["%", 15, 400, INK]], { anchor: "middle" });
type(svg, b, L.y + 60, "now", "label", { fill: INK, size: 7.6, weight: 650, anchor: "middle" });

// facts
const F = S.facts, fw = (W - 2 * M) / F.length, FY = SAFE.bottom - 52;
mk("line", { x1: M, y1: FY - 22, x2: W - M, y2: FY - 22, class: "lo thin" }, svg);
F.forEach((f, i) => {
  type(svg, M + i * fw, FY, f.value, "num", { size: 15, weight: 450, fill: TONE.hi });
  type(svg, M + i * fw, FY + 12, f.label, "label", { fill: TONE.muted, size: 7.4 });
});
type(svg, M, SAFE.bottom - 4, "Owning 5% or more makes you a major shareholder", "label", { fill: TONE.hi, size: 8.6, weight: 600 });
grain(0.09);
