// Weekly calendar, slide 1: one card per trading day. The date set large at the left; the day's events at the
// right, one line per kind ("Dividend · cum", "Rights · trading", "AGM"), each event a logo and ticker.
// Cards are as tall as their content; today's card carries the accent.
// DATA.slide: { week, total, days: [{ day, mon, dow, today, groups: [{ label, what, items: [{ sym, logo }] }] }] }
const D = DATA, S = D.slide;
setAccent(D.direction);

// the page: a dot floor, the month as a huge outlined watermark, a glow behind today's card
dotField(0, 0, W, H, { fx: W * 0.78, fy: 70, reach: 300, op: 0.4 });
frame(D);

// title: a huge light word, the week range beside it
type(svg, M - 2, 86, "This week", "hero", { size: 50, weight: 440 });
type(svg, W - M, 66, S.week, "label", { fill: TONE.hi, size: 9, weight: 650, anchor: "end" });
type(svg, W - M, 78, `${S.total} events`, "label", { fill: TONE.muted, size: 7.4, anchor: "end" });

// ---------------------------------------------------------------- layout: lines per day, then card heights
const X0 = M, X1 = W - M, DATEW = 50, LX = X0 + DATEW + 12, LABW = 86, CX = LX + LABW, CW = X1 - 10 - CX;
const chipW = (it) => 12 + it.sym.length * 5.5 + 10;
const plan = S.days.map((d) => {
  const lines = [];
  for (const g of d.groups) {
    let row = [], w = 0, first = true;
    const push = () => { lines.push({ g, first, items: row }); first = false; row = []; w = 0; };
    for (const it of g.items) {
      if (row.length && w + chipW(it) > CW) push();
      row.push(it); w += chipW(it);
    }
    if (row.length) push();
  }
  return lines;
});
const TOP = 104, BOTTOM = H - 42, GAP = 6, LINE = 15, PAD = 10;
const need = plan.map((l) => Math.max(2, l.length) * LINE + 2 * PAD);
const k = Math.min(1.35, (BOTTOM - TOP - GAP * (plan.length - 1)) / need.reduce((a, b) => a + b, 0));

let y = TOP;
S.days.forEach((d, i) => {
  const h = need[i] * k, cy = y + h / 2;
  if (d.today) glow(X0 + 40, cy, 150, h * 0.9, 0.2);
  const g = mk("g", {}, svg);
  mk("rect", { x: X0, y, width: X1 - X0, height: h, rx: 7,
    style: d.today ? `fill:${TONE.ground};fill-opacity:.55;stroke:var(--acc);stroke-width:1px` : `fill:${TONE.ground};fill-opacity:.6;stroke:${TONE.lo};stroke-width:1px` }, g);
  if (d.today) {
    mk("rect", { x: X1 - 40, y: y - 6, width: 32, height: 12, rx: 6, style: "fill:var(--acc);stroke:none" }, g);
    type(g, X1 - 24, y + 2.2, "TODAY", "caps", { fill: TONE.ground, size: 5, anchor: "middle" });
  }
  // the date block
  type(g, X0 + DATEW / 2 + 2, cy - 12, d.dow, "caps", { fill: d.today ? "var(--acc)" : TONE.faint, size: 5.4, anchor: "middle" });
  type(g, X0 + DATEW / 2 + 2, cy + 8, String(d.day).padStart(2, "0"), "num", { size: 24, weight: 280, fill: d.today ? "var(--acc)" : TONE.hi, anchor: "middle" });
  type(g, X0 + DATEW / 2 + 2, cy + 19, d.mon, "caps", { fill: TONE.faint, size: 5.4, anchor: "middle" });
  mk("line", { x1: X0 + DATEW + 2, y1: y + 8, x2: X0 + DATEW + 2, y2: y + h - 8, class: "lo thin" }, g);

  const lines = plan[i];
  if (!lines.length) type(g, LX, cy + 3, "No corporate actions", "label", { fill: TONE.faint, size: 7.4 });
  const lh = LINE * k, ly0 = cy - (lines.length * lh) / 2;
  lines.forEach((l, j) => {
    const by = ly0 + j * lh + lh * 0.5 + 3;
    if (l.first) {
      glyph(g, l.g.kind, LX + 3.5, by - 2, 3.3, l.g.what ? "var(--acc)" : TONE.muted);
      const t = type(g, LX + 11, by, l.g.label.toUpperCase(), "caps", { fill: TONE.muted, size: 5.2 });
      if (l.g.what) {
        const sp = mk("tspan", { style: "fill:var(--acc)" }, t);
        sp.textContent = ` · ${l.g.what.toUpperCase()}`;
      }
    }
    let x = CX;
    for (const it of l.items) { tickerChip(g, x, by, it.sym, it.logo, { size: 8.2 }); x += chipW(it); }
  });
  y += h + GAP;
});
grain();
