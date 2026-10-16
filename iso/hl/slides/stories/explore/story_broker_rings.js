// Top broker story, direction U: bubbles. Each of the top 8 brokers is a circle whose area is its value traded,
// its logo inside; a ring around each shows its lean: the green part what it bought, terracotta what it sold.
const D = DATA, R = D.rows;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
dotField(0, 0, W, H, { fx: W / 2, fy: 330, reach: 320, op: 0.28 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 44, R[0].name, "hero", { size: 34, weight: 650 });
type(svg, M, y0 + 62, `moved the most money · ${R[0].gross_s}`, "label", { fill: TONE.muted, size: 9.5 });
typeRun(svg, M, y0 + 80, [["ring: ", 8, 400, TONE.faint], ["bought", 8, 650, GI], ["  ·  ", 8, 400, TONE.faint], ["sold", 8, 650, TI]]);

// fixed, hand-tuned packing slots (centre-ish), radius by sqrt(value)
const SL = [[0.5, 0.36], [0.24, 0.62], [0.76, 0.6], [0.2, 0.2], [0.82, 0.22], [0.5, 0.83], [0.2, 0.9], [0.82, 0.9]];
const area = { x: M, y: y0 + 96, w: W - 2 * M, h: SAFE.bottom - 40 - (y0 + 96) };
const rmax = 74, rad = (r) => rmax * Math.sqrt(r.gross / R[0].gross);
R.slice(0, 8).forEach((r, i) => {
  const cx = area.x + SL[i][0] * area.w, cy = area.y + SL[i][1] * area.h, rr = rad(r);
  const pb = r.buy / (r.buy + r.sell), a0 = -Math.PI / 2, a1 = a0 + pb * Math.PI * 2, rr2 = rr + 4;
  const arc = (s, e, col) => mk("path", { d: `M${cx + rr2 * Math.cos(s)} ${cy + rr2 * Math.sin(s)}A${rr2} ${rr2} 0 ${e - s > Math.PI ? 1 : 0} 1 ${cx + rr2 * Math.cos(e)} ${cy + rr2 * Math.sin(e)}`,
    class: "nf", style: `stroke:${col};stroke-width:3px;stroke-linecap:butt` }, svg);
  mk("circle", { cx, cy, r: rr, style: `fill:${TONE.card};stroke:${TONE.mid};stroke-width:1px` }, svg);
  arc(a0 + 0.04, a1 - 0.04, G); arc(a1 + 0.04, a0 + Math.PI * 2 - 0.04, T);
  const lr = Math.max(9, rr * 0.36);
  logoChip(svg, cx, cy - rr * 0.22, lr, r.logo, r.code);
  type(svg, cx, cy + rr * 0.32, r.gross_s, "label", { fill: TONE.hi, size: Math.max(7, rr * 0.2), weight: 650, anchor: "middle" });
  if (rr > 34) type(svg, cx, cy + rr * 0.32 + rr * 0.2, r.code, "label", { fill: TONE.muted, size: Math.max(6, rr * 0.13), anchor: "middle" });
});

type(svg, M, SAFE.bottom - 4, `${D.market} traded on the IDX this week`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
