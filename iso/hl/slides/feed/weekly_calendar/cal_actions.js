// Weekly calendar, slide 3: the other corporate actions, one row each: the type, logo and ticker, the terms
// set large, and what it means in one plain line.
// DATA.slide: { title, rows: [{ sym, logo, kind, line, note }] }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.2, fy: H * 0.9, reach: 300, op: 0.36 });
frame(D);
const KIND = { "Rights issue": "rights", "Stock split": "split", "Warrant": "warrant", "AGM": "agm" };

para(svg, M, 74, S.title, "title");
const rows = S.rows, TOP = 98, RH = Math.min(54, (H - 50 - TOP) / rows.length);
rows.forEach((r, i) => {
  const y = TOP + i * RH, g = mk("g", {}, svg);
  mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, g);
  glyph(g, KIND[r.kind], M + 3.5, y + 12, 3.3, "var(--acc)");
  type(g, M + 11, y + 14, r.kind.toUpperCase(), "caps", { fill: "var(--acc)", size: 5.4 });
  tickerChip(g, M, y + 32, r.sym, r.logo, { size: 11 });
  if (r.line) type(g, 128, y + 30, r.line, "num", { size: 15, weight: 300, fill: TONE.hi });
  type(g, 128, y + 42, r.note, "label", { fill: TONE.muted, size: 7 });
});
mk("line", { x1: M, y1: TOP + rows.length * RH, x2: W - M, y2: TOP + rows.length * RH, class: "lo thin" }, svg);
grain();
