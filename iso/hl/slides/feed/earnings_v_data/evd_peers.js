// Earnings (data-led), slide 4: vs the sub-sector. Every peer that has reported the same quarter, ranked by
// how much its profit moved year on year; a centre zero line splits gains (right) from falls (left). Only the
// company is in the accent; the rank is the headline.
// DATA.slide: { title, sub, rows: [{sym, logo, g, s, hi, rank}], n, rank }
const D = DATA, S = D.slide, up = D.direction === "buy";
setAccent(D.direction);
const INK = up ? "#b2d2b9" : "#dc8d74";
frame(D);
const ty = para(svg, M, 74, S.title, "title", { maxW: W - 2 * M });
typeRun(svg, M - 1, ty + 50, [[`#${S.rank}`, 40, 400, TONE.hi], [`  of ${S.n} that reported`, 9, 500, TONE.muted]]);
type(svg, M, ty + 66, S.sub, "label", { fill: TONE.muted, size: 7.6 });
// the sector's icon, flush with the right margin and level with the rank block (its base on the rank's baseline)
if (S.sector) drawSectorIcon(svg, S.sector, { cx: W - M - 38, cy: ty + 36, S: 0.82 });

const rows = S.rows, top = ty + 84, bottom = 392, rh = Math.min(30, (bottom - top) / rows.length);
// keep wild peers (a +6,000% off a tiny base) from flattening the rest: bars stop at 1.6× the company's own
// move and end in a fade, the true number still printed
const me = rows.find((r) => r.hi), CAP = Math.max(0.5, Math.abs(me ? me.g : 1) * 1.6);
const cap = (v) => Math.max(-CAP, Math.min(CAP, v));
const gmax = Math.max(0.2, ...rows.map((r) => cap(r.g))), gmin = Math.min(0, ...rows.map((r) => cap(r.g)));
const BX0 = 104, BX1 = W - M - 40, xs = scale(gmin, gmax, BX0, BX1), z = xs(0);
const g = mk("g", {}, svg);
mk("line", { x1: z, y1: top - 4, x2: z, y2: top + rows.length * rh, style: `stroke:${TONE.mid};stroke-width:.8px` }, g);
rows.forEach((r, i) => {
  const cy = top + i * rh + rh / 2;
  if (r.hi) mk("rect", { x: M - 6, y: cy - rh / 2 + 2, width: W - 2 * M + 12, height: rh - 4, rx: 6, style: `fill:${TONE.card};stroke:none` }, g);
  type(g, M, cy + 3, `${r.rank}`, "label", { fill: r.hi ? INK : TONE.faint, size: 7.4, weight: 650 });
  tickerChip(g, M + 16, cy + 3, r.sym, r.logo, { size: 8.4, fill: r.hi ? TONE.hi : TONE.muted });
  const v = cap(r.g), x0 = Math.min(z, xs(v)), w = Math.max(1.5, Math.abs(xs(v) - z)), bh = r.hi ? 9 : 6;
  mk("rect", { x: x0, y: cy - bh / 2, width: w, height: bh, rx: bh / 2, style: r.hi ? "fill:var(--acc);stroke:none" : `fill:${TONE.mid};stroke:none` }, g);
  if (Math.abs(r.g) > CAP) { // a broken bar: two short slashes cut across its end
    const xe = xs(v) - (v > 0 ? 8 : -8);
    for (const d of [0, 3.2]) mk("line", { x1: xe + d - 1.6, y1: cy + bh, x2: xe + d + 1.6, y2: cy - bh, style: `stroke:${TONE.ground};stroke-width:1.6px` }, g);
  }
  const pos = v >= 0, tx = pos ? xs(v) + 5 : xs(v) - 5;
  type(g, tx, cy + 3, r.s + (r.g > 4 ? "" : ""), "label", { fill: r.hi ? INK : TONE.muted, size: r.hi ? 9 : 7.6, weight: r.hi ? 750 : 550, anchor: pos ? "start" : "end" });
});
grain(0.07);
