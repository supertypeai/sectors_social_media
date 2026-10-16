// Volume spike, round 2 variants. All lead with the size (rupiah value + shares) and keep the multiple as context.
// DATA.variant: "stack" | "calendar" | "ring" | "ticket"
const D = DATA, L = D.lead, up = D.dir === "buy";
setAccent(D.dir);
const INK = up ? "#b2d2b9" : "#dc8d74", FILL = up ? "#81a789" : "#c07159";
const rpv = (v) => (v >= 1e12 ? `Rp ${(v / 1e12).toFixed(1)} T` : v >= 1e9 ? `Rp ${(v / 1e9).toFixed(1)} B` : `Rp ${Math.round(v / 1e6)} M`);
const value = +L.value, price = +L.price, normalValue = +L.median * price, bars = L.bars;
dotField(0, 0, W, H, { fx: W * 0.7, fy: 300, reach: 320, op: 0.28 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "VOLUME SPIKE", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
logoChip(svg, M + 20, y0 + 42, 20, L.logo, L.sym);
type(svg, M + 50, y0 + 47, L.sym, "hero", { size: 34, weight: 650 });
type(svg, M + 50, y0 + 61, L.name, "label", { fill: TONE.muted, size: 8.5 });
const foot = () => {
  type(svg, M, SAFE.bottom - 4, `Price ${L.chgTxt} that day · busiest in ${L.rareHead}`, "label", { fill: TONE.hi, size: 9, weight: 600 });
  type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
};
const V = D.variant;

if (V === "stack") {
  // MONEY STACK: today's value as a tall stack of banknote slabs, next to a normal day's thin stack; slab = fixed Rp
  type(svg, M, y0 + 112, rpv(value), "num", { size: 44, weight: 550, fill: INK });
  type(svg, M, y0 + 130, `changed hands in one day · ${L.volumeTxt} shares`, "label", { fill: TONE.hi, size: 9.5, weight: 600 });
  const unit = Math.pow(10, Math.floor(Math.log10(value / 18))), nToday = Math.round(value / unit), nNorm = Math.max(1, Math.round(normalValue / unit));
  const base = SAFE.bottom - 48, sh = Math.min(13, (base - (y0 + 170)) / nToday), w = 92, dx = 16, dy = 9;
  const stack = (x, n, lit) => {
    for (let i = 0; i < n; i++) {
      const y = base - (i + 1) * sh;
      mk("path", { d: `M${x + w} ${y}L${x + w + dx} ${y - dy}V${y - dy + sh - 1.5}L${x + w} ${y + sh - 1.5}Z`, style: `fill:${lit ? "#5f7d66" : "#3a3f3b"}` }, svg);
      mk("rect", { x, y, width: w, height: sh - 1.5, style: `fill:${lit ? FILL : "#4f5550"}` }, svg);
      if (i === n - 1) mk("path", { d: `M${x} ${y}L${x + dx} ${y - dy}H${x + w + dx}L${x + w} ${y}Z`, style: `fill:${lit ? "#c5dccb" : "#7a827c"}` }, svg);
    }
    return base - n * sh - dy;
  };
  const tn = stack(M + 20, nNorm, false), tt = stack(W - M - w - dx - 20, nToday, true);
  type(svg, M + 20 + w / 2, tn - 8, rpv(normalValue), "label", { fill: TONE.hi, size: 9, weight: 650, anchor: "middle" });
  type(svg, M + 20 + w / 2, base + 14, "A NORMAL DAY", "caps", { fill: TONE.muted, size: 6, anchor: "middle" });
  type(svg, W - M - w / 2 - dx - 20, base + 14, "THIS DAY", "caps", { fill: INK, size: 6, anchor: "middle" });
  type(svg, W - M, tt - 8, `${L.ratioTxt}× normal`, "label", { fill: INK, size: 10, weight: 750, anchor: "end" });
  type(svg, M, base + 32, `1 slab = ${rpv(unit)}`, "label", { fill: TONE.faint, size: 7 });
} else if (V === "calendar") {
  // CALENDAR HEAT: the last 30 trading days as squares, shade = value traded; today's square big and lit
  type(svg, M, y0 + 112, rpv(value), "num", { size: 44, weight: 550, fill: INK });
  type(svg, M, y0 + 130, `traded on ${D.company} · ${L.volumeTxt} shares`, "label", { fill: TONE.hi, size: 9.5, weight: 600 });
  const cols = 6, cell = (W - 2 * M - (cols - 1) * 6) / cols, gy = y0 + 160, vmax = Math.max(...bars.map((b) => b.v));
  const days = bars.slice(0, -1);
  days.forEach((b, i) => {
    const c = i % cols, r = Math.floor(i / cols), t = Math.sqrt(b.v / vmax);
    mk("rect", { x: M + c * (cell + 6), y: gy + r * (cell * 0.62 + 6), width: cell, height: cell * 0.62, rx: 5, style: `fill:${TONE.hi};fill-opacity:${0.05 + 0.45 * t};stroke:none` }, svg);
  });
  const rows = Math.ceil(days.length / cols), ty = gy + rows * (cell * 0.62 + 6) + 10;
  mk("rect", { x: M, y: ty, width: W - 2 * M, height: 74, rx: 10, style: `fill:${FILL};stroke:none` }, svg);
  type(svg, M + 14, ty + 28, "THIS DAY", "caps", { fill: TONE.ground, size: 6.4, weight: 800 });
  type(svg, M + 14, ty + 56, `${L.ratioTxt}× a normal day`, "num", { size: 22, weight: 600, fill: TONE.ground });
  type(svg, W - M - 14, ty + 56, rpv(value), "num", { size: 18, weight: 600, fill: TONE.ground, anchor: "end" });
  type(svg, M, gy - 8, "LAST 30 TRADING DAYS · BRIGHTER = MORE TRADED", "caps", { fill: TONE.faint, size: 5.4 });
} else if (V === "ring") {
  // RING: a full circle is today's value; the slice a normal day fills is a thin wedge, so the size difference reads at once
  const cx = W / 2, cy = y0 + 250, R = 120, frac = Math.min(1, normalValue / value), a = frac * Math.PI * 2;
  mk("circle", { cx, cy, r: R, style: `fill:${FILL};fill-opacity:.9;stroke:none` }, svg);
  const p = (ang, r) => [cx + r * Math.sin(ang), cy - r * Math.cos(ang)];
  const [x1, y1] = p(0, R), [x2, y2] = p(a, R);
  mk("path", { d: `M${cx} ${cy}L${x1} ${y1}A${R} ${R} 0 ${a > Math.PI ? 1 : 0} 1 ${x2} ${y2}Z`, style: `fill:${TONE.ground};fill-opacity:.85;stroke:${TONE.hi};stroke-width:1px` }, svg);
  mk("circle", { cx, cy, r: R * 0.58, style: `fill:${TONE.ground};stroke:none` }, svg);
  type(svg, cx, cy + 4, rpv(value), "num", { size: 30, weight: 600, fill: INK, anchor: "middle" });
  type(svg, cx, cy + 22, `${L.volumeTxt} shares`, "label", { fill: TONE.hi, size: 9, anchor: "middle" });
  type(svg, cx, cy - 26, "THIS DAY", "caps", { fill: TONE.muted, size: 6, anchor: "middle" });
  const [lx, ly] = p(a / 2, R + 18);
  type(svg, lx + 4, ly, `a normal day: ${rpv(normalValue)}`, "label", { fill: TONE.hi, size: 8.6, weight: 650 });
  type(svg, M, cy + R + 52, `${L.ratioTxt}× a normal day`, "num", { size: 26, weight: 600, fill: TONE.hi });
  type(svg, M, cy + R + 68, "The dark slice is how much trades on a normal day.", "label", { fill: TONE.muted, size: 8.4 });
} else {
  // TICKET / TAPE: a market-tape receipt of the day — volume, value, price, multiple — like a printed slip
  const tx = M + 6, tw = W - 2 * M - 12, ty = y0 + 100, th = SAFE.bottom - 60 - ty;
  mk("rect", { x: tx, y: ty, width: tw, height: th, rx: 6, style: `fill:${TONE.card};stroke:${TONE.mid};stroke-width:1px` }, svg);
  for (let x = tx + 6; x < tx + tw - 6; x += 9) mk("circle", { cx: x, cy: ty, r: 2.2, style: `fill:${TONE.ground}` }, svg);
  type(svg, tx + 16, ty + 30, `${D.company.toUpperCase()} · ${L.sym}`, "caps", { fill: TONE.muted, size: 6.4, weight: 750 });
  type(svg, tx + 16, ty + 74, rpv(value), "num", { size: 40, weight: 550, fill: INK });
  type(svg, tx + 16, ty + 90, "value traded", "label", { fill: TONE.muted, size: 8.4 });
  const rows = [["Shares traded", `${L.volumeTxt}`], ["A normal day", `${L.medianTxt} shares · ${rpv(normalValue)}`], ["Times normal", `${L.ratioTxt}×`], ["Price", `Rp ${price.toLocaleString("en-US")} · ${L.chgTxt}`], ["Busiest in", L.rareHead]];
  rows.forEach(([k, v], i) => {
    const y = ty + 128 + i * 30;
    mk("line", { x1: tx + 16, y1: y - 18, x2: tx + tw - 16, y2: y - 18, style: `stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 3` }, svg);
    type(svg, tx + 16, y, k, "label", { fill: TONE.muted, size: 9 });
    type(svg, tx + tw - 16, y, v, "label", { fill: k === "Times normal" ? INK : TONE.hi, size: 10, weight: 650, anchor: "end" });
  });
  // mini bar strip at the bottom of the slip
  const sy = ty + th - 22, sw = (tw - 32) / bars.length, vmax = Math.max(...bars.map((b) => b.v));
  bars.forEach((b, i) => {
    const h = Math.max(1.5, 46 * (b.v / vmax)), last = i === bars.length - 1;
    mk("rect", { x: tx + 16 + i * sw, y: sy - h, width: sw - 1.5, height: h, style: `fill:${last ? FILL : TONE.mid}` }, svg);
  });
}
foot();
grain(0.08);
