// Volume spike story, frame 1: one tall bar over a month of calm bars, and the median it broke.
// DATA: { format:"story", kicker, company, source, dir, lead:{ sym, name, sector, logo, volumeTxt, medianTxt, ratioTxt,
//         chgTxt, rareHead, rareSub, foreignTxt, foreignSub, median, bars:[{d, v}] }, slide }
setAccent(DATA.dir);
dotField(0, 0, W, H, { fx: W * 0.72, fy: 330, reach: 300, op: 0.22 });
const L = DATA.lead, { top, bottom } = storyFrame(DATA);
const g = mk("g", {}, svg);

// who: logo, ticker, name and sector
logoChip(g, M + 13, top + 11, 13, L.logo, L.sym);
type(g, M + 33, top + 10, L.sym, "title", { size: 17, weight: 600 });
type(g, M + 33, top + 22, L.name, "label", { fill: TONE.muted, size: 7.4 });
if (L.sector) type(g, W - M, top + 10, L.sector, "caps", { fill: TONE.faint, anchor: "end" });

// the number: shares traded, and how many times a normal day
const hy = top + 86;
const hero = type(g, M - 2, hy, L.volumeTxt, "hero", { size: 66, weight: 380 });
const hw = hero.getBBox().width;
type(g, M + hw + 9, hy, "shares", "label", { fill: TONE.muted, size: 10 });
typeRun(g, M, hy + 28, [[`${L.ratioTxt}×`, 22, 500, "var(--acc)"], ["  a normal day", 13, 400, TONE.muted]]);

// the chart: last ~month of daily volume, the spike day last, the 30-day median dashed
const c = { x0: M, x1: W - M, y0: hy + 58, y1: bottom - 66 };
const bars = L.bars, n = bars.length, vmax = Math.max(...bars.map((b) => b.v));
const ys = scale(0, vmax, c.y1, c.y0), step = (c.x1 - c.x0) / n, bw = Math.max(2, step * 0.56);
mk("line", { x1: c.x0, y1: c.y1, x2: c.x1, y2: c.y1, class: "lo thin" }, g);
bars.forEach((b, i) => {
  const x = c.x0 + i * step + (step - bw) / 2, y = Math.min(ys(b.v), c.y1 - 1), last = i === n - 1;
  mk("rect", { x, y, width: bw, height: c.y1 - y, rx: 0.8,
    style: last ? "fill:var(--acc);fill-opacity:.9;stroke:none" : `fill:${TONE.mid};stroke:none` }, g);
});
const my = ys(L.median);
mk("line", { x1: c.x0, y1: my, x2: c.x1, y2: my, class: "dash nf" }, g);
// the median's key sits under the axis, never on the bars
const fd = (s) => fmtDay(dayOf(s));
mk("line", { x1: c.x0, y1: c.y1 + 9.5, x2: c.x0 + 12, y2: c.y1 + 9.5, class: "dash nf" }, g);
typeRun(g, c.x0 + 17, c.y1 + 12, [[`Normal day ${L.medianTxt}`, 7.2, 550, TONE.muted], [`  30-day median · since ${fd(bars[0].d)}`, 6.6, 450, TONE.faint]]);
type(g, c.x1, c.y1 + 12, fd(bars[n - 1].d), "label", { fill: TONE.hi, size: 6.6, anchor: "end", weight: 650 });

// three facts, quiet: price that day, how rare, foreign share of the trading
const fy = bottom - 18, cw = (W - 2 * M) / 3;
mk("line", { x1: M, y1: fy - 30, x2: W - M, y2: fy - 30, class: "lo thin" }, g);
[[L.chgTxt, "price that day"], [L.rareHead, L.rareSub], [L.foreignTxt, L.foreignSub]].forEach(([v, s], i) => {
  const x = M + i * cw;
  type(g, x, fy - 6, v, "num", { size: 19, weight: 400 });
  type(g, x, fy + 7, s, "label", { fill: TONE.muted, size: 6.8 });
});
grain(0.05);
