// Post #1, slide 1 (the hook): the question, and the stock's price over six months with the day of the move
// marked on it. One chart, one marker; the stats strip underneath carries the exact numbers.
// DATA.slide: { question, accent[], prices: [{date, close}], moveDate, moved, before, after, value, day, buy }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let ty = para(svg, M, 74, S.question, "title", { accent: S.accent ?? [], maxW: W - 2 * M });

// ---------------------------------------------------------------- the chart
const B = { x0: M, x1: W - M, y0: Math.max(150, ty + 46), y1: 344 };
// weekly closes keep the shape without the daily noise; the move day and the latest close stay exact
const tMove = dayOf(S.moveDate);
const daily = S.prices.map((p) => [dayOf(p.date), p.close]);
const px = weekly(daily.filter(([t]) => t !== tMove)).concat(daily.filter(([t]) => t === tMove), [daily.at(-1)])
  .sort((a, b) => a[0] - b[0]).filter((p, i, a) => !i || p[0] !== a[i - 1][0]);
const t0 = px[0][0], t1 = px.at(-1)[0], vals = px.map((p) => p[1]);
const lo = Math.min(...vals), hi = Math.max(...vals), pad = (hi - lo || hi * 0.1) * 0.22;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(lo - pad, hi + pad, B.y1, B.y0);
const pts = px.map(([t, v]) => [xs(t), ys(v)]);
const g = mk("g", {}, svg);

// faint price levels: low and high of the period, set small at the right
for (const v of [lo, hi]) {
  mk("line", { x1: B.x0, y1: ys(v), x2: B.x1, y2: ys(v), class: "lo thin", "stroke-dasharray": "1 3" }, g);
  type(g, B.x1, ys(v) - 3, rp(v), "label", { fill: TONE.faint, size: 6.2, anchor: "end" });
}
mk("line", { x1: B.x0, y1: B.y1, x2: B.x1, y2: B.y1, class: "lo thin" }, g);
xMonthsIn(g, xs, t0, t1, B.y1);

// before the move the line is quiet; from the move on it carries the accent
const tm = dayOf(S.moveDate), xm = xs(Math.min(Math.max(tm, t0), t1));
const before = pts.filter((p) => p[0] <= xm), after = pts.filter((p) => p[0] >= xm);
areaLine(g, before.length > 1 ? before : pts.slice(0, 2), B.y1, { color: TONE.edge, width: 1.5, fill: 0.08 });
if (after.length > 1) areaLine(g, [[xm, yAt(pts, xm)], ...after], B.y1, { color: "var(--acc)", width: 1.9, fill: 0.2 });

// the move: a rule from the top of the plot, a glowing dot on the line, the label above
const my = yAt(pts, xm);
mk("line", { x1: xm, y1: B.y0 - 6, x2: xm, y2: B.y1, style: "stroke:var(--acc);stroke-dasharray:2 3;stroke-width:1px" }, g);
glowDot(g, xm, my);
const right = xm < W * 0.62, lx = xm + (right ? 7 : -7), anchor = right ? "start" : "end";
type(g, lx, B.y0 + 4, `${S.moved.toFixed(1)}% ${S.buy ? "bought" : "sold"}`, "label", { fill: "var(--acc)", size: 13, weight: 700, anchor });
type(g, lx, B.y0 + 15, `by ${S.holder} · ${S.day}`, "label", { fill: TONE.muted, size: 7, anchor });

// today's price at the end of the line
const [ex, ey] = pts.at(-1);
mk("circle", { cx: ex, cy: ey, r: 2.4, style: `fill:${TONE.hi};stroke:${TONE.ground};stroke-width:1.2px` }, g);

// ---------------------------------------------------------------- stats strip
const stat = (x, yy, k, v, accent = false) => {
  type(svg, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(svg, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
const Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, svg);
stat(M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);

/** Month names under a plot whose baseline is at y1. */
function xMonthsIn(g, xs, t0, t1, y1) {
  const d = new Date(t0);
  d.setUTCDate(1);
  d.setUTCMonth(d.getUTCMonth() + 1);
  for (; d.getTime() <= t1; d.setUTCMonth(d.getUTCMonth() + 1)) {
    const x = xs(d.getTime());
    mk("line", { x1: x, y1, x2: x, y2: y1 + 3, class: "lo thin" }, g);
    type(g, x, y1 + 12, fmtMonth(d.getTime()), "label", { fill: TONE.faint, size: 6.4, anchor: "middle" });
  }
}
