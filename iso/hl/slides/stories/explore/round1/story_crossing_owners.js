// Story "crossing 5%", frame 2: who owns the company now, as ranked hairline bars on one 0–100% scale.
// The newcomer's bar is the accent; everyone else is grey; what is left is "everyone else", dashed.
// DATA.slide: { sym, logo, name, holder, rows: [{name, pct, mover}], note }
const D = DATA, S = D.slide;
setAccent(D.direction);
dotField(0, 0, W, H, { fx: W * 0.2, fy: H * 0.7, reach: 300, op: 0.2 });
const { top, bottom } = storyFrame(D);

logoChip(svg, M + 9, top + 12, 9, S.logo, S.sym);
type(svg, M + 25, top + 15.5, S.name, "label", { fill: TONE.muted, size: 8.6, weight: 550 });
let y = para(svg, M, top + 52, `Who owns ${S.sym} now`, "title");

const rest = Math.max(0, 100 - S.rows.reduce((s, r) => s + r.pct, 0));
const rows = S.rows.concat(rest >= 0.5 ? [{ name: "Everyone else", pct: rest, rest: true }] : []);
const x0 = M, x1 = W - M, bw = (v) => ((x1 - x0) * v) / 100;
const gap = Math.min(62, (bottom - 30 - (y + 44)) / rows.length);
let ry = y + 44;
for (const r of rows) {
  const fill = r.mover ? "var(--acc)" : r.rest ? TONE.faint : TONE.hi;
  // name, wrapped to two lines at most, and the stake at the right
  const lines = wrapText(r.name, 9, x1 - x0 - 70, 0.52).slice(0, 2);
  lines.forEach((l, i) => type(svg, x0, ry + i * 11, l, "label", { fill: r.mover ? TONE.hi : TONE.muted, size: 9, weight: r.mover ? 650 : 500 }));
  typeRun(svg, x1, ry + 2, [[r.pct.toFixed(r.pct >= 10 ? 1 : 2), 18, 400, r.mover ? "var(--acc)" : TONE.hi], ["%", 9, 400, TONE.muted]], { anchor: "end" });
  const by = ry + (lines.length - 1) * 11 + 9;
  mk("line", { x1: x0, y1: by, x2: x1, y2: by, class: "lo thin" }, svg);
  mk("line", { x1: x0, y1: by, x2: x0 + Math.max(1.5, bw(r.pct)), y2: by, class: "nf",
    style: `stroke:${fill};stroke-width:${r.mover ? 3 : 2}px;${r.rest ? "stroke-dasharray:2 3;" : ""}` }, svg);
  if (r.mover) type(svg, x0 + bw(r.pct) + 6, by + 2.5, "new", "caps", { fill: "var(--acc)", size: 5.6 });
  ry += Math.max(gap, (lines.length - 1) * 11 + 34);
}
type(svg, M, bottom - 2, S.note, "label", { fill: TONE.faint, size: 6.6 });
grain(0.05);
