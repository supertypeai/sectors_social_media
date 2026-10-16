// Top broker story, direction B: the leaderboard with sides. The 8 busiest brokers as thick bars true to scale,
// each split into what it bought (green) and what it sold (terracotta), so who leaned which way shows at once.
const D = DATA, rows = D.rows;
setAccent("buy");
const G = "#81a789", T = "#c07159", GI = "#b2d2b9", TI = "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.3, fy: 320, reach: 320, op: 0.28 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

typeRun(svg, M, y0 + 62, [[rows[0].name, 34, 650, TONE.hi]]);
type(svg, M, y0 + 82, `moved the most money · ${rows[0].gross_s} this week`, "label", { fill: TONE.muted, size: 9.5 });
// legend as words
typeRun(svg, M, y0 + 108, [["bought", 9, 650, GI], ["  ·  ", 9, 400, TONE.faint], ["sold", 9, 650, TI]]);

const TOP = y0 + 128, BOT = SAFE.bottom - 30, RH = (BOT - TOP) / rows.length, X0 = M + 40, X1 = W - M;
const max = Math.max(...rows.map((r) => r.buy + r.sell));
rows.forEach((r, i) => {
  const y = TOP + i * RH, bh = Math.min(20, RH * 0.48), by = y + RH * 0.42;
  logoChip(svg, M + 14, by + bh / 2, 14, r.logo, r.code);
  const wb = (X1 - X0) * (r.buy / max), ws = (X1 - X0) * (r.sell / max);
  mk("rect", { x: X0, y: by, width: wb, height: bh, rx: 2, style: `fill:${G};fill-opacity:.85;stroke:none` }, svg);
  mk("rect", { x: X0 + wb + 1.5, y: by, width: ws, height: bh, rx: 2, style: `fill:${T};fill-opacity:.85;stroke:none` }, svg);
  typeRun(svg, X0, by - 4, [[r.code, 7.4, 750, TONE.hi], [`  ${r.name}`, 7.4, 450, TONE.muted]]);
  const lean = r.net >= 0;
  type(svg, X1, by - 4, `${r.gross_s} · net ${r.net_s}`, "label", { fill: lean ? GI : TI, size: 7.4, weight: 600, anchor: "end" });
});

type(svg, M, SAFE.bottom - 4, `Market traded ${D.market} this week`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
