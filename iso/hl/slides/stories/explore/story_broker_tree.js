// Top broker story, direction T: a market-share map. The week's broker value as one tall rectangle split into
// tiles sized by share (squarified treemap): the top 8 brokers, each with its logo, and "everyone else".
const D = DATA, R = D.rows;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
const top8 = R.reduce((s, r) => s + r.share, 0);
typeRun(svg, M, y0 + 50, [[`${Math.round(top8)}%`, 40, 500, INK], [" of the money", 22, 500, TONE.hi]]);
type(svg, M, y0 + 70, `went through just 8 of ${D.nbrokers} brokers`, "label", { fill: TONE.muted, size: 9.5 });

// squarified treemap
const items = R.map((r) => ({ ...r, v: r.share })).concat([{ code: "", name: "Everyone else", v: 100 - top8, rest: true }]);
const box = { x: M, y: y0 + 88, w: W - 2 * M, h: SAFE.bottom - 30 - (y0 + 88) };
function squarify(list, b) {
  const out = [];
  let rest = list.slice(), r = { ...b };
  const total = list.reduce((s, i) => s + i.v, 0), scaleA = (b.w * b.h) / total;
  while (rest.length) {
    const short = Math.min(r.w, r.h);
    let row = [rest[0]], worst = Infinity;
    const ratio = (rw) => { const s = rw.reduce((a, i) => a + i.v * scaleA, 0), mx = Math.max(...rw.map((i) => i.v * scaleA)), mn = Math.min(...rw.map((i) => i.v * scaleA)); return Math.max((short * short * mx) / (s * s), (s * s) / (short * short * mn)); };
    worst = ratio(row);
    for (let k = 1; k < rest.length; k++) { const nr = ratio(rest.slice(0, k + 1)); if (nr > worst) break; worst = nr; row = rest.slice(0, k + 1); }
    const s = row.reduce((a, i) => a + i.v * scaleA, 0), thick = s / short;
    let off = 0;
    for (const it of row) {
      const len = (it.v * scaleA) / thick;
      out.push(r.w >= r.h ? { ...it, x: r.x, y: r.y + off, w: thick, h: len } : { ...it, x: r.x + off, y: r.y, w: len, h: thick });
      off += len;
    }
    if (r.w >= r.h) { r.x += thick; r.w -= thick; } else { r.y += thick; r.h -= thick; }
    rest = rest.slice(row.length);
  }
  return out;
}
squarify(items, box).forEach((t, i) => {
  const g = 2, first = i === 0, x = t.x + g, y = t.y + g, w = t.w - 2 * g, h = t.h - 2 * g;
  mk("rect", { x, y, width: w, height: h, rx: 6, style: t.rest ? `fill:none;stroke:${TONE.mid};stroke-width:1px;stroke-dasharray:2 3`
    : first ? `fill:${FILL};fill-opacity:.3;stroke:${FILL};stroke-width:1.2px` : `fill:${TONE.card};stroke:${TONE.mid};stroke-width:1px` }, svg);
  const big = Math.min(w, h) > 70, mid = Math.min(w, h) > 44;
  if (t.rest) {
    type(svg, x + 10, y + 18, "Everyone else", "label", { fill: TONE.muted, size: 9, weight: 600 });
    type(svg, x + 10, y + 30, `${Math.round(t.v)}%`, "label", { fill: TONE.faint, size: 8 });
    return;
  }
  const lr = big ? 18 : mid ? 12 : 9;
  logoChip(svg, x + 9 + lr, y + 9 + lr, lr, t.logo, t.code);
  if (mid) {
    type(svg, x + 10, y + h - (big ? 24 : 18), `${t.share.toFixed(1)}%`, "num", { size: big ? 24 : 15, weight: 450, fill: first ? INK : TONE.hi });
    type(svg, x + 10, y + h - 9, `${t.code} · ${t.gross_s}`, "label", { fill: TONE.muted, size: big ? 8 : 6.6 });
  } else {
    type(svg, x + 9 + 2 * lr + 4, y + 9 + lr + 3, `${t.code} ${t.share.toFixed(0)}%`, "label", { fill: TONE.hi, size: 7, weight: 650 });
  }
});

type(svg, M, SAFE.bottom - 4, `Share of all broker value · ${D.market} traded`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
