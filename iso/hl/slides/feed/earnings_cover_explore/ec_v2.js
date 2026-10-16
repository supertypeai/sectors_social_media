// Earnings cover, round 2: the chart / object carries the story; the number is a label on it, not the hero.
// DATA.slide.variant: "line" | "bars" | "glass"     DATA.slide: { sym, name, logo, hero, up, head, series[{label,v}], prev, now_s }
const D = DATA, S = D.slide, up = S.up === true || S.up === "True";
setAccent(up ? "buy" : "sell");
const FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74";
const rs = (v) => { const a = Math.abs(v); return a >= 1e12 ? `Rp ${(a / 1e12).toFixed(1)} T` : `Rp ${Math.round(a / 1e9)} B`; };
const ser = S.series, n = ser.length, now = ser[n - 1], yago = ser.find((q) => q.label === S.prev) ?? ser[n - 5];
frame(D);

// header: logo + ticker, then one plain sentence with the number inside it
logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });
typeRun(svg, M, 122, [[up ? "Profit " : "Profit ", 26, 600, TONE.hi], [up ? `up ${S.hero}` : `down ${S.hero.replace("−", "")}`, 26, 700, INK]]);
type(svg, M, 142, `${now.label.replace("-", " ")} vs ${yago.label.replace("-", " ")} · ${S.head}`, "label", { fill: TONE.muted, size: 8.5 });

const V = S.variant;
if (V === "line") {
  // 12 quarters of profit as a big area chart; the year-ago point and this quarter marked and joined
  const q = ser.slice(-12), B = { x0: M, x1: W - M - 6, y0: 186, y1: H - 70 };
  const vmax = Math.max(...q.map((p) => p.v)), vmin = Math.min(0, ...q.map((p) => p.v));
  const xs = (i) => B.x0 + (i / (q.length - 1)) * (B.x1 - B.x0), ys = scale(vmin, vmax * 1.15, B.y1, B.y0);
  const pts = q.map((p, i) => [xs(i), ys(p.v)]);
  areaLine(svg, pts, B.y1, { color: FILL, width: 2.2, fill: 0.18 });
  mk("line", { x1: B.x0, y1: B.y1, x2: B.x1, y2: B.y1, class: "lo thin" }, svg);
  const ia = q.indexOf(yago), ib = q.length - 1;
  if (ia >= 0) {
    mk("line", { x1: pts[ia][0], y1: pts[ia][1], x2: pts[ib][0], y2: pts[ib][1], style: `stroke:${TONE.hi};stroke-width:1px;stroke-dasharray:3 3` }, svg);
    glowDot(svg, ...pts[ia], TONE.hi, 3.4);
    type(svg, pts[ia][0], pts[ia][1] - 12, rs(yago.v), "label", { fill: TONE.hi, size: 9, weight: 650, anchor: "middle" });
    type(svg, pts[ia][0], pts[ia][1] - 3.5, "a year ago", "label", { fill: TONE.muted, size: 6.6, anchor: "middle" });
  }
  glowDot(svg, ...pts[ib], FILL, 4.5);
  type(svg, pts[ib][0] - 2, pts[ib][1] - 14, rs(now.v), "num", { size: 18, weight: 650, fill: INK, anchor: "end" });
  [0, 4, 8, 11].forEach((i) => q[i] && type(svg, xs(i), B.y1 + 12, q[i].label.replace("-20", " '"), "label", { fill: TONE.faint, size: 6.6, anchor: i === 11 ? "end" : i ? "middle" : "start" }));
  type(svg, M, H - 46, "Net profit, last 12 quarters", "label", { fill: TONE.muted, size: 7.4 });
} else if (V === "bars") {
  // two thick horizontal bars, year-ago vs now, true to scale, with the gap shaded and labelled
  const span = W - 2 * M, max = Math.max(yago.v, now.v), y1 = 180, y2 = 262, bh = 46;
  const bar = (y, v, label, fill, ink) => {
    const w = Math.max(6, span * (v / max));
    mk("rect", { x: M, y, width: w, height: bh, rx: 6, style: `fill:${fill};stroke:none` }, svg);
    type(svg, M, y - 8, label.replace("-", " ").toUpperCase(), "caps", { fill: TONE.muted, size: 6.4, weight: 750 });
    const inside = w > 130;
    type(svg, inside ? M + 12 : M + w + 10, y + bh / 2 + 7, rs(v), "num", { size: 22, weight: 600, fill: inside ? TONE.ground : ink });
    return w;
  };
  const wa = bar(y1, yago.v, yago.label, TONE.mid, TONE.hi);
  const wb = bar(y2, now.v, now.label, FILL, INK);
  // the difference as a bracket between the two bar ends
  const xa = M + wa, xb = M + wb;
  mk("path", { d: `M${xa} ${y1 + bh + 6}V${y1 + bh + 18}H${xb}V${y2 - 6}`, class: "nf", style: `stroke:${INK};stroke-width:1.4px;stroke-dasharray:3 2` }, svg);
  type(svg, (xa + xb) / 2, y1 + bh + 32, `${up ? "+" : "−"}${rs(Math.abs(now.v - yago.v))}`, "label", { fill: INK, size: 11, weight: 750, anchor: "middle" });
  // a mini context strip: the last 8 quarters as ticks
  const q = ser.slice(-8), sy = H - 50, sw = (W - 2 * M) / q.length, smax = Math.max(...q.map((p) => p.v));
  type(svg, M, sy - 46, "LAST 8 QUARTERS", "caps", { fill: TONE.faint, size: 5.6 });
  q.forEach((p, i) => {
    const h = Math.max(2, 34 * (Math.max(0, p.v) / smax)), x = M + i * sw + 4;
    mk("rect", { x, y: sy - h, width: sw - 8, height: h, rx: 2, style: `fill:${p === now ? FILL : p === yago ? TONE.hi : TONE.lo};fill-opacity:${p === yago ? 0.5 : 1};stroke:none` }, svg);
  });
  mk("line", { x1: M, y1: sy, x2: W - M, y2: sy, class: "lo thin" }, svg);
} else {
  // object: two glasses filled to profit (true to scale), the new one in the accent, a measuring scale between
  const gx = [M + 50, W - M - 120], gw = 74, gTop = 190, gBot = H - 92, max = Math.max(yago.v, now.v);
  const glass = (x, v, label, fill, ink, lit) => {
    const h = (gBot - gTop - 10) * (v / max), top = gBot - h;
    // the liquid, with a soft meniscus
    mk("path", { d: `M${x + 3} ${top}Q${x + gw / 2} ${top + 5} ${x + gw - 3} ${top}V${gBot - 3}H${x + 3}Z`, style: `fill:${fill};fill-opacity:${lit ? 0.85 : 0.5};stroke:none` }, svg);
    if (lit) for (let k = 0; k < 6; k++) mk("circle", { cx: x + 14 + (k * 11) % (gw - 24), cy: gBot - 12 - ((k * 37) % Math.max(10, h - 20)), r: 1.4 + (k % 3) * 0.5, style: "fill:#ffffff;fill-opacity:.35" }, svg);
    // the glass: hairline walls, rim ellipse, base
    mk("path", { d: `M${x} ${gTop}V${gBot}H${x + gw}V${gTop}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1.4px` }, svg);
    mk("ellipse", { cx: x + gw / 2, cy: gTop, rx: gw / 2, ry: 5, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, svg);
    // the value sits above the rim so it never lands on the liquid
    type(svg, x + gw / 2, gTop - 12, rs(v), "num", { size: lit ? 18 : 14, weight: 650, fill: ink, anchor: "middle" });
    type(svg, x + gw / 2, gBot + 14, label.replace("-", " ").toUpperCase(), "caps", { fill: lit ? INK : TONE.muted, size: 6.4, weight: 750, anchor: "middle" });
  };
  glass(gx[0], yago.v, yago.label, TONE.hi, TONE.hi, false);
  glass(gx[1], now.v, now.label, FILL, INK, true);
  // measuring ticks between the glasses
  const mx = (gx[0] + gw + gx[1]) / 2;
  for (let k = 0; k <= 10; k++) {
    const y = gBot - (gBot - gTop - 10) * (k / 10);
    mk("line", { x1: mx - (k % 5 ? 3 : 7), y1: y, x2: mx + (k % 5 ? 3 : 7), y2: y, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
  }
  type(svg, mx, gTop - 12, "NET PROFIT", "caps", { fill: TONE.faint, size: 5.6, anchor: "middle" });
}
grain(0.08);
