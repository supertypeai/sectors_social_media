// Weekly calendar hook, variant B: the week as five tall day tiles side by side, like a wall planner. Each tile:
// the weekday, the date huge, then that day's events stacked as logo + ticker under small type icons.
// Today's tile is filled with the accent tint. Same DATA as cal_week.
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.5, fy: 110, reach: 320, op: 0.36 });
frame(D);

type(svg, M - 2, 86, "This week", "hero", { size: 50, weight: 440 });
type(svg, W - M, 66, S.week, "label", { fill: TONE.hi, size: 9, weight: 650, anchor: "end" });
type(svg, W - M, 78, `${S.total} events`, "label", { fill: TONE.muted, size: 7.4, anchor: "end" });

const n = S.days.length, GAP = 5, TW = (W - 2 * M - GAP * (n - 1)) / n, TOP = 104, BOT = H - 42;
S.days.forEach((d, i) => {
  const x = M + i * (TW + GAP), g = mk("g", {}, svg), cx = x + TW / 2;
  if (d.today) glow(cx, TOP + 40, 60, 90, 0.2);
  mk("rect", { x, y: TOP, width: TW, height: BOT - TOP, rx: 8,
    style: d.today ? "fill:var(--acc);fill-opacity:.08;stroke:var(--acc);stroke-width:1px" : `fill:${TONE.ground};fill-opacity:.6;stroke:${TONE.lo};stroke-width:1px` }, g);
  type(g, cx, TOP + 14, d.dow, "caps", { fill: d.today ? "var(--acc)" : TONE.faint, size: 5.4, anchor: "middle" });
  type(g, cx, TOP + 42, String(d.day), "num", { size: 30, weight: 260, fill: d.today ? "var(--acc)" : TONE.hi, anchor: "middle" });
  mk("line", { x1: x + 8, y1: TOP + 54, x2: x + TW - 8, y2: TOP + 54, class: "lo thin" }, g);

  // events: per kind, an icon + short label, then one ticker per line
  const items = d.groups.reduce((s, gr) => s + 1 + gr.items.length, 0);
  const room = BOT - 10 - (TOP + 64), step = Math.min(13.5, room / Math.max(1, items));
  let y = TOP + 68;
  for (const gr of d.groups) {
    glyph(g, gr.kind, x + 10, y - 2, 2.8, gr.what ? "var(--acc)" : TONE.muted);
    const SHORT = { Dividend: "Div", Rights: "Rights", Split: "Split", Warrant: "Warr.", AGM: "AGM", IPO: "IPO" };
    type(g, x + 16, y, `${SHORT[gr.label] ?? gr.label}${gr.what ? " · " + gr.what : ""}`.toUpperCase(), "caps", { fill: TONE.muted, size: 4.2 });
    y += step * 0.95;
    for (const it of gr.items) {
      tickerChip(g, x + 6, y, it.sym, it.logo, { size: Math.min(7.6, step * 0.58) });
      y += step;
    }
    y += step * 0.25;
  }
});
grain();
