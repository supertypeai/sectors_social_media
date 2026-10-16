// Post #1, slide 4: the short version. The holder's stake over the past year as a step chart (the move is the
// accent step), three facts in a row under it, then the question for the comments.
// DATA.slide: { title, accent[], stake: [{date, pct}], moveDate, facts: [{value, label, accent?}], question, cta }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let ty = para(svg, M, 74, S.title, "title", { accent: S.accent ?? [] });

// ---------------------------------------------------------------- the stake, step by step
const B = { x0: M + 4, x1: W - M - 4, y0: ty + 40, y1: 236 };
const st = S.stake.map((p) => [dayOf(p.date), p.pct]);
const t0 = st[0][0], t1 = st.at(-1)[0], top = Math.max(...st.map((p) => p[1])) * 1.18 || 1;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(0, top, B.y1, B.y0);
const steps = [];
st.forEach(([t, v], i) => { if (i) steps.push([xs(t), ys(st[i - 1][1])]); steps.push([xs(t), ys(v)]); });
const g = mk("g", {}, svg);
mk("line", { x1: M, y1: B.y1, x2: W - M, y2: B.y1, class: "lo thin" }, g);
areaLine(g, steps, B.y1, { color: TONE.hi, width: 1.6, fill: 0.1, smooth: false });

// the move: its vertical step redrawn in the accent, with the change written beside it
// the move is the biggest step in the history
let k = 0;
st.forEach(([, v], i) => { if (i && Math.abs(v - st[i - 1][1]) > (k ? Math.abs(st[k][1] - st[k - 1][1]) : 0)) k = i; });
if (k > 0) {
  const x = xs(st[k][0]), ya = ys(st[k - 1][1]), yb = ys(st[k][1]);
  mk("path", { d: `M${x} ${ya}V${yb}`, class: "nf", style: "stroke:var(--acc);stroke-width:2.6px" }, g);
  glowDot(g, x, yb);
  const diff = st[k][1] - st[k - 1][1], left = x > W * 0.55;
  type(g, x + (left ? -8 : 8), (ya + yb) / 2 + 4, `${diff > 0 ? "+" : "−"}${Math.abs(diff).toFixed(1)} pts`, "label", { fill: "var(--acc)", size: 12, weight: 700, anchor: left ? "end" : "start" });
}
// first and last values, and the dates under the ends
type(g, xs(t0), ys(st[0][1]) - 6, `${st[0][1].toFixed(2)}%`, "label", { fill: TONE.muted, size: 7.4, weight: 600 });
type(g, xs(t1), ys(st.at(-1)[1]) - 6, `${st.at(-1)[1].toFixed(2)}%`, "label", { fill: TONE.hi, size: 8.4, weight: 650, anchor: "end" });
type(g, B.x0, B.y1 + 11, fmtDay(t0), "label", { fill: TONE.faint, size: 6.4 });
type(g, B.x1, B.y1 + 11, "now", "label", { fill: TONE.faint, size: 6.4, anchor: "end" });

// ---------------------------------------------------------------- three facts in a row
const FY = 280, cw = (W - 2 * M) / 3;
mk("line", { x1: M, y1: FY - 18, x2: W - M, y2: FY - 18, class: "lo thin" }, svg);
S.facts.slice(0, 3).forEach((f, i) => {
  const x = M + i * cw;
  if (i) mk("line", { x1: x - 8, y1: FY - 10, x2: x - 8, y2: FY + 22, class: "lo thin" }, svg);
  type(svg, x, FY + 4, f.value, "num", { size: f.value.length > 8 ? 17 : 21, weight: 280, fill: f.accent ? "var(--acc)" : TONE.hi });
  type(svg, x, FY + 18, f.label, "label", { fill: TONE.muted, size: 6.8 });
});
mk("line", { x1: M, y1: FY + 34, x2: W - M, y2: FY + 34, class: "lo thin" }, svg);

// ---------------------------------------------------------------- the question
para(svg, M, FY + 66, S.question, "title", { fill: TONE.hi, maxW: W - 2 * M });
type(svg, M, H - 46, S.cta, "label", { fill: "var(--acc)", size: 8.5, weight: 650 });
type(svg, W - M, H - 46, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
