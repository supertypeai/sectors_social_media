// Top broker story, direction P: a podium. The top 3 brokers stand on blocks whose heights are their value
// traded, their logos large on top; #1 in the centre. Places 4–8 follow as one quiet line of logos.
const D = DATA, R = D.rows;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
dotField(0, 0, W, H, { fx: W / 2, fy: 300, reach: 300, op: 0.3 });
glow(W / 2, 250, 170, 150, 0.2);

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "TOP BROKERS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 46, "Who moved", "hero", { size: 34, weight: 500 });
type(svg, M, y0 + 82, "the most money", "hero", { size: 34, weight: 500, fill: INK });
typeRun(svg, M, y0 + 104, [["bought", 9, 650, "#b2d2b9"], ["  ·  ", 9, 400, TONE.faint], ["sold", 9, 650, "#dc8d74"]]);

// the podium: order 2 · 1 · 3, block heights true to value
const base = y0 + 352, maxH = 150, cw = 92, gap = 8, order = [1, 0, 2];
const x0 = (W - 3 * cw - 2 * gap) / 2;
order.forEach((ri, k) => {
  const r = R[ri], h = maxH * (r.gross / R[0].gross), x = x0 + k * (cw + gap), top = base - h, first = ri === 0;
  // the block is the broker's value, split into what it bought (green, bottom) and sold (terracotta, top)
  const hb = h * (r.buy / (r.buy + r.sell));
  const cp = mk("clipPath", { id: `pod${k}` }, mk("defs", {}, svg));
  mk("rect", { x, y: top, width: cw, height: h, rx: 6 }, cp);
  const gg = mk("g", { "clip-path": `url(#pod${k})` }, svg);
  mk("rect", { x, y: top, width: cw, height: h - hb, style: "fill:#c07159;fill-opacity:.55;stroke:none" }, gg);
  mk("rect", { x, y: top + h - hb, width: cw, height: hb, style: "fill:#81a789;fill-opacity:.55;stroke:none" }, gg);
  mk("line", { x1: x, y1: top + h - hb, x2: x + cw, y2: top + h - hb, style: `stroke:${TONE.ground};stroke-width:1.5px` }, gg);
  mk("rect", { x, y: top, width: cw, height: h, rx: 6, style: `fill:none;stroke:${first ? INK : TONE.mid};stroke-width:${first ? 1.4 : 1}px` }, svg);
  type(svg, x + cw / 2, top + 40, String(ri + 1), "num", { size: 40, weight: 300, fill: TONE.hi, anchor: "middle" });
  const lean = r.net >= 0;
  type(svg, x + cw / 2, top + 56, `net ${lean ? "buy" : "sell"} ${r.net_s.replace(/^[+−-]/, "")}`, "label", { fill: TONE.hi, size: 7.2, weight: 650, anchor: "middle" });
  logoChip(svg, x + cw / 2, top - 30, first ? 26 : 21, r.logo, r.code);
  type(svg, x + cw / 2, top - (first ? 64 : 58), r.code, "label", { fill: TONE.hi, size: 9, weight: 750, anchor: "middle" });
  type(svg, x + cw / 2, base - 26, r.gross_s, "label", { fill: first ? TONE.hi : TONE.hi, size: first ? 12 : 10.5, weight: 650, anchor: "middle" });
  type(svg, x + cw / 2, base - 13, r.name, "label", { fill: TONE.muted, size: 7, anchor: "middle" });
});
mk("line", { x1: M, y1: base, x2: W - M, y2: base, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);

// places 4–8
const ly = base + 46;
type(svg, M, ly - 22, "THEN", "caps", { fill: TONE.faint, size: 5.6 });
const step = (W - 2 * M) / 5;
R.slice(3, 8).forEach((r, i) => {
  const cx = M + step * (i + 0.5);
  logoChip(svg, cx, ly, 15, r.logo, r.code);
  type(svg, cx, ly + 28, `${i + 4} · ${r.code}`, "label", { fill: TONE.hi, size: 8, weight: 700, anchor: "middle" });
  type(svg, cx, ly + 39, r.gross_s, "label", { fill: TONE.muted, size: 7.2, anchor: "middle" });
  // a small buy/sell split bar
  const bw = 40, pb = r.buy / (r.buy + r.sell);
  mk("rect", { x: cx - bw / 2, y: ly + 45, width: bw * pb - 0.5, height: 3, rx: 1, style: "fill:#81a789;stroke:none" }, svg);
  mk("rect", { x: cx - bw / 2 + bw * pb + 0.5, y: ly + 45, width: bw * (1 - pb) - 0.5, height: 3, rx: 1, style: "fill:#c07159;stroke:none" }, svg);
});

type(svg, M, SAFE.bottom - 4, `${D.market} traded on the IDX this week`, "label", { fill: TONE.hi, size: 9, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
