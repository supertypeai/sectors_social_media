// Style B, the poster: one numeral as big as the slide allows, and under it one bar that is the whole
// company, owners in order, with the sold piece pulled down out of it in the accent.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

// the numeral, across the full width
typeRun(svg, M - 6, 196, [[S.hero.num, 150, 200], [S.hero.unit, 60, 220, TONE.muted]]);
let y = para(svg, M, 236, S.title, "title", { accent: S.accent });

// the company as one bar, 100% wide: everyone else, Elaine Low, kept, then the sold gap
const B = { x: M, y: 330, w: W - 2 * M, h: 16 }, xOf = (pct) => B.x + (pct / 100) * B.w;
const parts = [...S.segments.map((s) => ({ ...s })), { pct: S.sold.pct, kind: "sold" }];
let acc = 0;
for (const p of parts) {
  const x0 = xOf(acc), x1 = xOf(acc + p.pct) - 1.5;
  acc += p.pct;
  if (p.kind === "sold") {
    // the slot it left, dashed, and the piece itself dropped below
    mk("rect", { x: x0, y: B.y, width: x1 - x0, height: B.h, rx: 2, class: "dash nf" }, svg);
    mk("rect", { x: x0, y: B.y + 30, width: x1 - x0, height: B.h, rx: 2, style: "fill:var(--acc);stroke:none" }, svg);
    type(svg, x1, B.y + 30 + B.h + 13, `${p.pct.toFixed(2)}% sold`, "label", { fill: "var(--acc)", size: 9, weight: 650, anchor: "end" });
    for (const xx of [x0, x1]) mk("line", { x1: xx, y1: B.y + B.h + 2, x2: xx, y2: B.y + 28, class: "dash nf" }, svg);
  } else {
    mk("rect", { x: x0, y: B.y, width: x1 - x0, height: B.h, rx: 2, style: `fill:${p.kind === "kept" ? TONE.hi : TONE.mid};stroke:none` }, svg);
    type(svg, x0, B.y - 6, `${p.label} ${p.pct.toFixed(1)}%`, "label", { fill: p.kind === "kept" ? TONE.hi : TONE.faint, size: 6.6 });
  }
}
type(svg, M, 402, S.line, "body", { fill: TONE.muted });
