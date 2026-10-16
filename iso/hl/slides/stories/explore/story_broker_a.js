// Top broker story, direction A: spotlight (the volume-spike E layout). The broker with the biggest net
// position: its code as a big badge, two numbers side by side, its day-by-day net as large diverging bars,
// and the three stocks behind it with logos.
const D = DATA, S = D.spot, up = S.net > 0;
setAccent(up ? "buy" : "sell");
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";
dotField(0, 0, W, H, { fx: W * 0.75, fy: 300, reach: 320, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, `BIGGEST NET ${up ? "BUYER" : "SELLER"}`, "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

// the broker: its logo, name and code
logoChip(svg, M + 21, y0 + 42, 21, S.logo, S.code);
type(svg, M + 52, y0 + 44, S.name, "hero", { size: 26, weight: 650 });
type(svg, M + 52, y0 + 59, `${S.code} · ${S.foreign ? "foreign" : "local"} broker · #${S.rank} by value traded`, "label", { fill: TONE.muted, size: 8.5 });

// two numbers
typeRun(svg, M, y0 + 132, [[S.net_s, 46, 500, INK]]);
type(svg, M, y0 + 150, `net ${up ? "bought" : "sold"} this week`, "label", { fill: TONE.muted, size: 9 });
typeRun(svg, W - M, y0 + 132, [[S.gross_s, 30, 450, TONE.hi]], { anchor: "end" });
type(svg, W - M, y0 + 150, "traded in total", "label", { fill: TONE.muted, size: 9, anchor: "end" });

// day by day: diverging bars around zero
const B = { x0: M, x1: W - M, y0: y0 + 180, y1: y0 + 330 }, n = S.daily.length;
const vmax = Math.max(...S.daily.map((d) => Math.abs(d.v))) || 1, vmin = Math.min(0, ...S.daily.map((d) => d.v)), vtop = Math.max(0, ...S.daily.map((d) => d.v));
const ys = scale(vmin * 1.15, vtop * 1.15 || vmax * 0.2, B.y1, B.y0), zy = ys(0), bw = (B.x1 - B.x0) / n;
type(svg, M, B.y0 - 8, "NET, DAY BY DAY", "caps", { fill: TONE.faint, size: 5.6 });
S.daily.forEach((d, i) => {
  const x = B.x0 + i * bw + 8, y = Math.min(ys(d.v), zy), h = Math.abs(ys(d.v) - zy), same = d.v * S.net > 0;
  mk("rect", { x, y, width: bw - 16, height: Math.max(1.5, h), rx: 2, style: same ? `fill:${FILL};stroke:none` : `fill:none;stroke:${TONE.edge};stroke-width:1px` }, svg);
  const below = d.v < 0;
  type(svg, x + (bw - 16) / 2, below ? y + h + 11 : y - 4, d.s.replace("Rp ", ""), "label", { fill: same ? INK : TONE.muted, size: 7.4, weight: 600, anchor: "middle" });
  type(svg, x + (bw - 16) / 2, B.y1 + 16, d.dow.toUpperCase(), "caps", { fill: TONE.faint, size: 5.6, anchor: "middle" });
});
mk("line", { x1: B.x0, y1: zy, x2: B.x1, y2: zy, style: `stroke:${TONE.edge};stroke-width:.8px` }, svg);

// the stocks behind it
const SY = B.y1 + 44;
type(svg, M, SY, `MOSTLY ${up ? "BUYING" : "SELLING"}`, "caps", { fill: TONE.faint, size: 5.6 });
S.stocks.forEach((s, i) => {
  const x = M + i * ((W - 2 * M) / 3), y = SY + 26;
  logoChip(svg, x + 13, y - 4, 13, s.logo, s.sym);
  type(svg, x + 32, y - 2, s.sym, "label", { fill: TONE.hi, size: 11, weight: 700 });
  type(svg, x + 32, y + 10, s.s, "label", { fill: INK, size: 8, weight: 600 });
});

type(svg, M, SAFE.bottom - 4, `Following ${S.code} next week?`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
