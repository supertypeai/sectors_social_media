// Hook for BYAN as a technical drawing: the mine cart stays the focal point, framed like a spec sheet —
// registration corners, a dimension line, two annotation leaders and a small spec table. Every number is
// from DATA; the coal is still the only accent.
const D = DATA, S = D.slide;
setAccent(D.direction);
drawFlameMark(mk("g", { opacity: 0.14 }, svg), { S: 2.5, cx: 292, cy: 176, dropCls: "sil", floorOn: false });
frame(D);

typeRun(svg, M - 3, 118, [[S.hero.num, 82, 220], [S.hero.unit, 34, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 148, sentence, "title", { accent: [] });
type(svg, M, y + 17, S.deal ? `${S.seller} → ${S.holder}` : `in one filing, on ${S.day}`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- the drawing area: registration corners
const A = { x0: M, y0: 214, x1: W - M, y1: H - 82 }; // ends above the spec table
const g = mk("g", {}, svg);
for (const [x, yy, dx, dy] of [[A.x0, A.y0, 1, 1], [A.x1, A.y0, -1, 1], [A.x0, A.y1, 1, -1], [A.x1, A.y1, -1, -1]]) {
  mk("path", { d: `M${x} ${yy + dy * 9}V${yy}H${x + dx * 9}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, g);
}
type(g, A.x0 + 13, A.y0 + 4, "FIG. 1", "caps", { fill: TONE.faint, size: 5.6 });
type(g, A.x1 - 13, A.y0 + 4, `${D.company.split(" · ")[0]} / COAL`, "caps", { fill: TONE.faint, size: 5.6, anchor: "end" });

// the object
const cart = drawMineCart(svg, { S: 1.7, cx: 190, cy: 302 });
const P = cart.K.P;

// leaders: the coal (accent) and the tub that is left
leader(svg, P(10, 6, 44), [W - M - 64, 240], [[`${S.sold.pct.toFixed(1)}% ${S.verb}`, "label", { fill: "var(--acc)", weight: 700, size: 10 }], [S.day, "label", { fill: TONE.muted, size: 6.6 }]], { cls: "dash nf acc" });
leader(svg, P(-28, 17, 22), [M + 54, 300], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 10 }], [`from ${S.before.toFixed(2)}%`, "label", { fill: TONE.muted, size: 6.6 }]], { anchor: "end" });

// ---------------------------------------------------------------- spec table, bottom
const rows = [["HOLDER", S.holder], ["BEFORE", `${S.before.toFixed(2)}%`], ["AFTER", `${S.after.toFixed(2)}%`], ["FILED", S.day]];
const TY = H - 62, colW = (W - 2 * M) / rows.length;
mk("line", { x1: M, y1: TY - 12, x2: W - M, y2: TY - 12, class: "lo thin" }, svg);
rows.forEach(([k, v], i) => {
  const x = M + i * colW;
  if (i) mk("line", { x1: x - 6, y1: TY - 8, x2: x - 6, y2: TY + 10, class: "lo thin" }, svg);
  type(svg, x, TY - 2, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(svg, x, TY + 9, v.length > 16 ? v.slice(0, 15) + "…" : v, "label", { fill: TONE.hi, size: 8, weight: 600 });
});
