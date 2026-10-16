// Weekly calendar hook, variant C: the week as a chart made of logos. One column per trading day; every event is
// a company logo, piled up from the baseline, so the busiest day is the tallest stack. The number of events is
// the headline. Same DATA as cal_week.
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.5, fy: 300, reach: 300, op: 0.36 });
frame(D);

typeRun(svg, M - 3, 112, [[String(S.total), 84, 420, "var(--acc)"], [" events", 26, 440, TONE.hi]]);
type(svg, M, 134, `on the IDX this week · ${S.week}`, "label", { fill: TONE.muted, size: 9 });

const n = S.days.length, CW = (W - 2 * M) / n, BASE = H - 92, R = 16, COLS = 2;
const counts = S.days.map((d) => d.groups.reduce((s, g) => s + g.items.length, 0));
const busiest = counts.indexOf(Math.max(...counts));
// size the bubbles so the tallest stack fits between the headline and the baseline
const rows = Math.ceil(Math.max(...counts) / COLS), r = Math.min(R, (BASE - 160) / (rows * 2.15), CW / (COLS * 2.4));

S.days.forEach((d, i) => {
  const cx = M + CW * (i + 0.5), hot = i === busiest, g = mk("g", {}, svg);
  if (hot) glow(cx, BASE - rows * r, CW * 0.8, rows * r * 1.4, 0.18);
  const items = d.groups.flatMap((gr) => gr.items.map((it) => ({ ...it, kind: gr.kind })));
  items.forEach((it, k) => {
    const col = k % COLS, row = Math.floor(k / COLS);
    const x = cx + (col - (COLS - 1) / 2) * r * 2.15 + (row % 2 ? r * 0.25 : -r * 0.25);
    const y = BASE - r - 2 - row * r * 2.1;
    logoChip(g, x, y, r, it.logo, it.sym);
  });
  // the count above the stack
  const top = BASE - Math.ceil(items.length / COLS) * r * 2.1 - 10;
  type(g, cx, top, String(items.length), "num", { size: 13, weight: 300, fill: hot ? "var(--acc)" : TONE.hi, anchor: "middle" });
  // the day under the baseline
  type(g, cx, BASE + 16, d.dow, "caps", { fill: hot ? "var(--acc)" : TONE.faint, size: 5.6, anchor: "middle" });
  type(g, cx, BASE + 32, String(d.day), "num", { size: 16, weight: 280, fill: hot ? "var(--acc)" : TONE.hi, anchor: "middle" });
  if (d.today) type(g, cx, BASE + 44, "TODAY", "caps", { fill: "var(--acc)", size: 4.8, anchor: "middle" });
});
mk("line", { x1: M, y1: BASE + 3, x2: W - M, y2: BASE + 3, class: "lo" }, svg);
type(svg, W - M, H - 42, "Swipe for dividends and corporate actions →", "label", { fill: TONE.muted, size: 7, anchor: "end" });
grain();
