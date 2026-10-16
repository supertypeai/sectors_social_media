// Earnings cover, animated (slide 1 as a video). PROG 0 → 1:
//   0.00–0.25  header and the sentence fade/slide in
//   0.20–0.55  the year-ago bar grows, its value counts up
//   0.50–0.85  this quarter's bar grows past it, value counts up, the "+Rp X" bracket draws
//   0.80–1.00  the 8-quarter strip rises; the finished frame is the still cover
// DATA.slide: { sym, name, logo, hero, up, head, series[{label,v}], prev }
const D = DATA, S = D.slide, up = S.up === true || S.up === "True";
setAccent(up ? "buy" : "sell");
const FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74";
const P = typeof PROG === "number" ? PROG : 1;
const win = (a, b) => Math.max(0, Math.min(1, (P - a) / (b - a)));
const ease = (t) => 1 - Math.pow(1 - t, 3);
const rs = (v) => { const a = Math.abs(v); return a >= 1e12 ? `Rp ${(a / 1e12).toFixed(1)} T` : `Rp ${Math.round(a / 1e9)} B`; };
const ser = S.series, n = ser.length, now = ser[n - 1], yago = ser.find((q) => q.label === S.prev) ?? ser[n - 5];
frame(D);

// header + sentence
const h = ease(win(0, 0.25)), hg = mk("g", { opacity: h, transform: `translate(0 ${(1 - h) * 10})` }, svg);
logoChip(hg, M + 15, 66, 15, S.logo, S.sym);
type(hg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(hg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });
typeRun(hg, M, 122, [["Profit ", 26, 600, TONE.hi], [up ? `up ${S.hero}` : `down ${S.hero.replace("−", "")}`, 26, 700, INK]]);
type(hg, M, 142, `${now.label.replace("-", " ")} vs ${yago.label.replace("-", " ")} · ${S.head}`, "label", { fill: TONE.muted, size: 8.5 });

// the two bars
const span = W - 2 * M, max = Math.max(yago.v, now.v), y1 = 180, y2 = 262, bh = 46;
const bar = (y, v, label, fill, ink, t, darkText) => {
  if (t <= 0) return 0;
  const full = Math.max(6, span * (v / max)), w = full * ease(t);
  type(svg, M, y - 8, label.replace("-", " ").toUpperCase(), "caps", { fill: TONE.muted, size: 6.4, weight: 750 });
  mk("rect", { x: M, y, width: w, height: bh, rx: 6, style: `fill:${fill};stroke:none` }, svg);
  const inside = full > 130, val = rs(v * ease(t));
  type(svg, inside ? M + 12 : M + w + 10, y + bh / 2 + 7, val, "num", { size: 22, weight: 600, fill: inside ? darkText : ink });
  return full;
};
const wa = bar(y1, yago.v, yago.label, TONE.mid, TONE.hi, win(0.2, 0.55), TONE.hi);
const wb = bar(y2, now.v, now.label, FILL, INK, win(0.5, 0.85), TONE.ground);
// the difference bracket draws in
const bt = ease(win(0.72, 0.88));
if (bt > 0) {
  const xa = M + wa, xb = M + wb, len = Math.abs(xb - xa) + 30;
  mk("path", { d: `M${xa} ${y1 + bh + 6}V${y1 + bh + 18}H${xb}V${y2 - 6}`, class: "nf",
    style: `stroke:${INK};stroke-width:1.4px;stroke-dasharray:${len};stroke-dashoffset:${len * (1 - bt)}` }, svg);
  const lg = mk("g", { opacity: bt }, svg);
  type(lg, (xa + xb) / 2, y1 + bh + 32, `${up ? "+" : "−"}${rs(Math.abs(now.v - yago.v))}`, "label", { fill: INK, size: 11, weight: 750, anchor: "middle" });
}
// the 8-quarter strip
const st = win(0.8, 1), q = ser.slice(-8), sy = H - 50, sw = (W - 2 * M) / q.length, smax = Math.max(...q.map((p) => p.v));
if (st > 0) {
  const sg = mk("g", { opacity: ease(st) }, svg);
  type(sg, M, sy - 46, "LAST 8 QUARTERS", "caps", { fill: TONE.faint, size: 5.6 });
  q.forEach((p, i) => {
    const hh = Math.max(2, 34 * (Math.max(0, p.v) / smax)) * ease(Math.max(0, Math.min(1, st * 1.6 - i * 0.08)));
    mk("rect", { x: M + i * sw + 4, y: sy - hh, width: sw - 8, height: hh, rx: 2, style: `fill:${p === now ? FILL : p === yago ? TONE.hi : TONE.lo};fill-opacity:${p === yago ? 0.5 : 1};stroke:none` }, sg);
  });
  mk("line", { x1: M, y1: sy, x2: W - M, y2: sy, class: "lo thin" }, sg);
}
grain(0.08);
