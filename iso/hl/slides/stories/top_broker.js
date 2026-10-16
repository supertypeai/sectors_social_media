// Top broker story, direction E: an editorial top 5. Huge outlined rank numerals, the logo and name beside each,
// the value large, and one small lean marker. Magazine list, no chart chrome.
const D = DATA, R = D.rows.slice(0, 5);
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 48, "The week's", "hero", { size: 36, weight: 500 });
type(svg, M, y0 + 86, "top 5 brokers", "hero", { size: 36, weight: 500, fill: GI });

const TOP = y0 + 112, RH = (SAFE.bottom - 34 - TOP) / R.length;
R.forEach((r, i) => {
  const y = TOP + i * RH, cy = y + RH / 2, first = i === 0;
  // the rank, huge and outlined
  const n = type(svg, M - 4, cy + 30, String(i + 1), "hero", { size: 84, weight: 700 });
  n.style.fill = first ? "#81a789" : "none"; n.style.fillOpacity = first ? 0.25 : 1;
  n.style.stroke = first ? GI : TONE.mid; n.style.strokeWidth = "1px";
  logoChip(svg, M + 74, cy - 8, 17, r.logo, r.code);
  type(svg, M + 98, cy - 10, r.name, "label", { fill: TONE.hi, size: 13, weight: 650 });
  const lean = r.net >= 0;
  typeRun(svg, M + 98, cy + 4, [[r.code, 8, 750, TONE.muted], [`  ·  Net ${lean ? "Buyer" : "Seller"} ${r.net_s.replace(/^[+−-]/, "")}`, 8, 500, lean ? GI : TI]]);
  type(svg, W - M, cy - 4, r.gross_s, "num", { size: first ? 26 : 21, weight: 450, fill: first ? GI : TONE.hi, anchor: "end" });
  // bought vs sold: one split bar across the row, with the two amounts at its ends
  const bx0 = M + 98, bx1 = W - M, by = cy + 18, pb = r.buy / (r.buy + r.sell), bm = bx0 + (bx1 - bx0) * pb;
  mk("rect", { x: bx0, y: by, width: bm - bx0 - 1, height: 4, rx: 1.5, style: "fill:#81a789;stroke:none" }, svg);
  mk("rect", { x: bm + 1, y: by, width: bx1 - bm - 1, height: 4, rx: 1.5, style: "fill:#c07159;stroke:none" }, svg);
  const rs = (v) => (v >= 1e12 ? `${(v / 1e12).toFixed(1)} T` : `${Math.round(v / 1e9)} B`);
  type(svg, bx0, by + 13, `Bought ${rs(r.buy)}`, "label", { fill: GI, size: 6.8, weight: 600 });
  type(svg, bx1, by + 13, `Sold ${rs(r.sell)}`, "label", { fill: TI, size: 6.8, weight: 600, anchor: "end" });
  if (i < R.length - 1) mk("line", { x1: M + 74, y1: y + RH, x2: W - M, y2: y + RH, class: "lo thin" }, svg);
});

type(svg, M, SAFE.bottom - 4, `By value traded · ${D.market} on the IDX this week`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
