// Style C, the waffle: the company as 100 squares, one per percent. The sold ones are lit in the accent,
// the kept ones bright outlines, everyone else faint. You count it before you read it.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

// headline left, the count as the number
typeRun(svg, M - 3, 104, [[S.hero.num, 64, 220], [S.hero.unit, 28, 250, TONE.muted]]);
para(svg, M, 132, S.title, "title", { accent: S.accent, maxW: W - 2 * M });

// 10 × 10, filled bottom-up in owner order: everyone else, Elaine Low, kept, then sold on top
const N = 10, GAP = 3.2, SIDE = 200, CELL = (SIDE - GAP * (N - 1)) / N, X0 = M, Y0 = 196;
const kinds = [];
for (const s of S.segments) for (let i = 0; i < Math.round(s.pct); i++) kinds.push(s.kind);
for (let i = 0; i < Math.round(S.sold.pct); i++) kinds.push("sold");
while (kinds.length < 100) kinds.splice(0, 0, "other");
kinds.length = 100;
kinds.forEach((k, i) => {
  const r = N - 1 - Math.floor(i / N), c = i % N, x = X0 + c * (CELL + GAP), y = Y0 + r * (CELL + GAP);
  const style = k === "sold" ? "fill:var(--acc);stroke:none" : k === "kept" ? `fill:none;stroke:${TONE.hi};stroke-width:1.2px` : `fill:${TONE.lo};stroke:none`;
  mk("rect", { x, y, width: CELL, height: CELL, rx: 2, style }, svg);
});

// the key, set beside the grid: one line per kind, biggest meaning first
const KX = X0 + SIDE + 16;
const key = [["sold", `${S.sold.pct.toFixed(1)}%`, `sold by ${S.holder}`], ["kept", `${S.after.toFixed(1)}%`, "kept"], ["other", `${(100 - S.before).toFixed(1)}%`, "everyone else"]];
key.forEach(([k, v, label], i) => {
  const y = Y0 + 14 + i * 40;
  const fill = k === "sold" ? "var(--acc)" : k === "kept" ? TONE.hi : TONE.faint;
  type(svg, KX, y, v, "num", { size: 20, weight: 300, fill });
  type(svg, KX, y + 12, label, "label", { size: 7, fill: TONE.muted });
});
type(svg, M, Y0 + SIDE + 26, S.line, "body", { fill: TONE.muted });
