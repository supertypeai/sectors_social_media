// Volume spike story, frame 2: every spike of the day, ranked by how many times a normal day it traded.
// DATA: { format:"story", kicker, company, source, dir, count, rows:[{ sym, logo, ratio, ratioTxt, volumeTxt, chgTxt }], slide }
// Bars are on a log scale (a 170× outlier would flatten a 4× next to it); the multiple is written on every row.
setAccent(DATA.dir);
dotField(0, 0, W, H, { fx: W * 0.3, fy: 300, reach: 300, op: 0.18 });
const { top, bottom } = storyFrame(DATA);
const g = mk("g", {}, svg);

type(g, M, top + 22, `${DATA.count} stocks traded`, "title", { size: 22, weight: 500 });
type(g, M, top + 46, "3× their normal day or more", "title", { size: 22, weight: 500, fill: TONE.muted });

const rows = DATA.rows, y0 = top + 82, rh = Math.min(54, (bottom - 20 - y0) / rows.length);
const lmax = Math.log(Math.max(...rows.map((r) => r.ratio))), lmin = Math.log(1);
const bx0 = M + 92, bx1 = W - M - 62, bs = scale(lmin, lmax, 0, bx1 - bx0);
rows.forEach((r, i) => {
  const y = y0 + i * rh, lead = i === 0;
  tickerChip(g, M, y + 6, r.sym, r.logo, { size: 10.5 });
  type(g, M + 17, y + 19, `${r.volumeTxt} sh · ${r.chgTxt}`, "label", { fill: TONE.faint, size: 6.8 });
  mk("line", { x1: bx0, y1: y + 2, x2: bx1, y2: y + 2, class: "lo thin" }, g);
  mk("rect", { x: bx0, y: y - 1, width: Math.max(2, bs(Math.log(r.ratio))), height: 6, rx: 3,
    style: lead ? "fill:var(--acc);stroke:none" : `fill:${TONE.edge};stroke:none` }, g);
  type(g, W - M, y + 7, `${r.ratioTxt}×`, "num", { size: 17, weight: 400, anchor: "end", fill: lead ? TONE.hi : TONE.muted });
});
type(g, M, bottom - 2, "Times a normal day (30-day median volume)", "label", { fill: TONE.faint, size: 6.6 });
grain(0.05);
