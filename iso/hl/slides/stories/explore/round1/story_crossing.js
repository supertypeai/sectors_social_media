// Story "crossing 5%", frame 1: who crossed, the stake now set big, and the stake as steps climbing through a
// dashed 5% line (the step that crosses it is the accent). A quiet row of three numbers closes it.
// DATA.slide: { holder, sym, logo, name, before, after, now, day, stake: [{date, pct}], facts: [{value, label}] }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.8, fy: H * 0.62, reach: 300, op: 0.22 });
const { top, bottom } = storyFrame(D);

// ---------------------------------------------------------------- who, and the stake now
logoChip(svg, M + 9, top + 12, 9, S.logo, S.sym);
type(svg, M + 25, top + 15.5, S.name, "label", { fill: TONE.muted, size: 8.6, weight: 550 });
let y = para(svg, M, top + 52, S.holder, "title", { maxW: W - 2 * M, lh: 1.1 });
type(svg, M, y + 26, "now owns", "caps", { fill: TONE.faint });
const heroY = y + 92;
typeRun(svg, M - 3, heroY, [[S.now.toFixed(2), 76, 300, TONE.hi], ["%", 30, 300, TONE.muted]]);
type(svg, M, heroY + 20, S.before > 0 ? `of ${S.sym}, up from ${S.before.toFixed(2)}% before ${S.day}` : `of ${S.sym}, a new holder since ${S.day}`, "label", { fill: TONE.muted, size: 8.4 });

// ---------------------------------------------------------------- the stake as steps through the 5% line
const B = { x0: M + 2, x1: W - M - 2, y0: heroY + 44, y1: bottom - 62 };
const st = S.stake.map((p) => [dayOf(p.date), p.pct]);
const t0 = st[0][0], t1 = st.at(-1)[0];
const hi = Math.max(6, ...st.map((p) => p[1])) * 1.15;
const xs = scale(t0, t1, B.x0, B.x1), ys = scale(0, hi, B.y1, B.y0);
const g = mk("g", {}, svg);
mk("line", { x1: M, y1: B.y1, x2: W - M, y2: B.y1, class: "lo thin" }, g);

// the threshold: dashed, labelled at the left above it
const y5 = ys(5);
mk("line", { x1: M, y1: y5, x2: W - M, y2: y5, class: "nf", style: `stroke:${TONE.edge};stroke-width:.9px;stroke-dasharray:3 3` }, g);
type(g, M, y5 - 5, "5% · major-holder line", "caps", { fill: TONE.muted, size: 5.8 });
// (the start level is labelled below its line, so it never meets this label)

const steps = [];
st.forEach(([t, v], i) => { if (i) steps.push([xs(t), ys(st[i - 1][1])]); steps.push([xs(t), ys(v)]); });
areaLine(g, steps, B.y1, { color: TONE.hi, width: 1.5, fill: 0.08, smooth: false });

// the crossing step (before < 5 <= after) in the accent, a dot where it lands
const k = st.findIndex(([, v], i) => i && st[i - 1][1] < 5 && v >= 5);
if (k > 0) {
  const x = xs(st[k][0]), ya = ys(st[k - 1][1]), yb = ys(st[k][1]);
  mk("path", { d: `M${x} ${ya}V${yb}`, class: "nf", style: "stroke:var(--acc);stroke-width:2.4px" }, g);
  glowDot(g, x, yb, "var(--acc)", 3.2);
  // the date sits above the dot, clear of the line that runs on to the right
  const anchor = x > W - M - 30 ? "end" : x < M + 30 ? "start" : "middle";
  type(g, x + (anchor === "end" ? 4 : anchor === "start" ? -4 : 0), yb - 12, S.day, "label", { fill: TONE.hi, size: 8, weight: 600, anchor });
}
// the starting level, written on the line where it begins (below it when it sits just under the 5% line)
const ys0 = ys(st[0][1]), below = B.y1 - ys0 > 16;
type(g, B.x0 + 2, below ? ys0 + 12 : ys0 - 5, `${st[0][1].toFixed(2)}%`, "label", { fill: TONE.muted, size: 8, weight: 600 });
type(g, B.x0, B.y1 + 12, fmtDay(t0), "label", { fill: TONE.faint, size: 6.6 });
type(g, B.x1, B.y1 + 12, "today", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });

// ---------------------------------------------------------------- three numbers, no boxes
const facts = S.facts.slice(0, 3), cw = (W - 2 * M) / facts.length, FY = bottom - 14;
facts.forEach((f, i) => {
  const x = M + i * cw;
  type(svg, x, FY, f.value, "num", { size: 15, weight: 400, fill: TONE.hi });
  type(svg, x, FY + 13, f.label, "caps", { fill: TONE.faint, size: 5.6 });
});
grain(0.05);
