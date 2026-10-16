// Earnings cover, animated (bars). The words are set from frame 1; the chart moves.
// PROG 0 → 1:
//   0.05–0.35  last year's bar grows; its value counts up (NumberFlow digits)
//   0.30–0.70  this quarter's bar grows past it with the company logo riding its tip; its value counts up
//   0.62–0.82  the gap bracket draws; a pill with the multiple and the rupiah change counts up on it
//   0.70–1.00  the last 8 quarters rise one after another; this quarter lands last and glows
// DATA.slide: { sym, name, logo, hero, up, head, series[{label,v}], prev }
const D = DATA, S = D.slide, up = S.up === true || S.up === "True";
setAccent(up ? "buy" : "sell");
const FILL = up ? "#81a789" : "#c07159", INK = up ? "#b2d2b9" : "#dc8d74";
const P = typeof PROG === "number" ? PROG : 1;
const win = (a, b) => Math.max(0, Math.min(1, (P - a) / (b - a)));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
const ser = S.series, n = ser.length, now = ser[n - 1], yago = ser.find((q) => q.label === S.prev) ?? ser[n - 5];
const unitOf = (v) => (Math.abs(v) >= 1e12 ? [1e12, "T"] : [1e9, "B"]);
frame(D);

/** NumberFlow digits (same as the insider cover): each digit spins to its new value, slots grow/shrink. */
function numberFlow(g, x, y, a, b, t, size, color, decimals = 1, weight = 600) {
  const A = a.toFixed(decimals), B = b.toFixed(decimals), n2 = Math.max(A.length, B.length);
  const pa = A.padStart(n2, " "), pb = B.padStart(n2, " "), upd = b >= a;
  const cw = size * 0.6, dot = size * 0.3, lh = size * 0.95, wOf = (c) => (c === "." ? dot : c === " " ? 0 : cw);
  const prog = [...pb].map((_, i) => { const lt = Math.max(0, Math.min(1, (t - (i / n2) * 0.3) / 0.7)); return ease(lt); });
  const widths = [...pb].map((c, i) => wOf(pa[i]) + (wOf(c) - wOf(pa[i])) * prog[i]);
  const total = widths.reduce((s, v) => s + v, 0), maxW = Math.max(...[pa, pb].map((s) => [...s].reduce((q, c) => q + wOf(c), 0)));
  const id = `nf${Math.round(x)}${Math.round(y)}`, defs = mk("defs", {}, g);
  const lgd = mk("linearGradient", { id: `${id}g`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  [[0, 0], [0.22, 1], [0.82, 1], [1, 0]].forEach(([o, a2]) => mk("stop", { offset: o, "stop-color": "#fff", "stop-opacity": a2 }, lgd));
  const mask = mk("mask", { id, maskUnits: "userSpaceOnUse", x: x - 4, y: y - size * 0.98, width: maxW + 8, height: size * 1.25 }, defs);
  mk("rect", { x: x - 4, y: y - size * 0.98, width: maxW + 8, height: size * 1.25, style: `fill:url(#${id}g);stroke:none` }, mask);
  const gg = mk("g", { mask: `url(#${id})` }, g);
  let cx = x;
  for (let i = 0; i < n2; i++) {
    let ca = pa[i], cb = pb[i];
    const wi = widths[i], e = prog[i];
    if (ca === " " && /\d/.test(cb)) ca = "0";
    if (cb === " " && /\d/.test(ca)) cb = "0";
    const fadeSlot = pa[i] === " " ? e : pb[i] === " " ? 1 - e : 1;
    const put = (ch, dy, op) => {
      op *= fadeSlot;
      if (op <= 0.01 || ch === " ") return;
      type(gg, cx + wi / 2, y + dy, ch, "num", { size, weight, fill: color, anchor: "middle" }).setAttribute("opacity", op.toFixed(3));
    };
    if (/\d/.test(ca) && /\d/.test(cb) && ca !== cb) {
      const da = +ca, db = +cb, steps = upd ? (db - da + 10) % 10 : (da - db + 10) % 10;
      const pos = steps * e, k = Math.floor(pos), f = pos - k, dir = upd ? -1 : 1;
      const d1 = (upd ? da + k : da - k + 10) % 10, d2 = (upd ? da + k + 1 : da - k - 1 + 20) % 10;
      put(String(d1), dir * lh * f, 1 - f);
      if (f > 0) put(String(d2), -dir * lh * (1 - f), f);
    } else if (ca === cb) put(cb, 0, 1);
    cx += wi;
  }
  return total;
}
/** "Rp" + counting digits + unit, at (x, y); returns the width. */
function money(g, x, y, v, t, size, color) {
  const [div, u] = unitOf(v);
  const w0 = type(g, x, y, "Rp", "num", { size: size * 0.62, weight: 500, fill: color }).getBBox().width;
  const w1 = numberFlow(g, x + w0 + 4, y, 0, v / div, t, size, color, v / div >= 100 ? 0 : 1);
  type(g, x + w0 + 4 + w1 + 3, y, u, "num", { size: size * 0.62, weight: 500, fill: color });
  return w0 + w1 + 20;
}

// ---------------------------------------------------------------- the words (static)
logoChip(svg, M + 15, 66, 15, S.logo, S.sym);
type(svg, M + 37, 70, S.sym, "label", { fill: TONE.hi, size: 14, weight: 800 });
type(svg, M + 37, 80, S.name, "label", { fill: TONE.muted, size: 7.4 });
typeRun(svg, M, 122, [["Profit ", 26, 600, TONE.hi], [up ? `up ${S.hero}` : `down ${S.hero.replace("−", "")}`, 26, 700, INK]]);
type(svg, M, 142, `${now.label.replace("-", " ")} vs ${yago.label.replace("-", " ")} · ${S.head}`, "label", { fill: TONE.muted, size: 8.5 });

// ---------------------------------------------------------------- the two bars
// span leaves room for the logo coin at the tip of the longer bar
const span = W - 2 * M - 32, max = Math.max(yago.v, now.v), y1 = 186, y2 = 270, bh = 46;
function bar(y, v, label, fill, ink, t, lit, pad = 0) {
  const lg = mk("g", { opacity: ease(Math.min(1, t * 4)) }, svg);
  type(lg, M, y - 9, label.replace("-", " ").toUpperCase(), "caps", { fill: lit ? INK : TONE.muted, size: 6.4, weight: 750 });
  const full = Math.max(8, span * (v / max)), w = full * ease(t);
  if (w > 0.5) mk("rect", { x: M, y, width: w, height: bh, rx: 6, style: `fill:${fill};stroke:none` }, svg);
  const inside = full > 150;
  money(mk("g", { opacity: ease(Math.min(1, t * 4)) }, svg), inside ? M + 12 : M + w + 12 + pad, y + bh / 2 + 8, v, t, 22, inside ? (lit ? TONE.ground : TONE.hi) : ink);
  return { w, full };
}
const A = bar(y1, yago.v, yago.label, TONE.mid, TONE.hi, win(0.05, 0.35), false);
const tb = win(0.3, 0.7), rr = 13, B = bar(y2, now.v, now.label, FILL, INK, tb, true, 2 * rr + 6);
// the logo rides the tip of this quarter's bar (vertically centred on it, clear of the quarter label)
if (tb > 0) {
  const cx = M + B.w + rr + 2, cy = y2 + bh / 2 - 2;
  mk("circle", { cx, cy: cy + 3, r: rr, style: `fill:${up ? "#5f7d66" : "#8f5444"}` }, svg);
  mk("circle", { cx, cy, r: rr + 1.5, style: `fill:${up ? "#c5dccb" : "#e9b9a9"}` }, svg);
  logoChip(svg, cx, cy, rr - 1, S.logo, S.sym);
}

// ---------------------------------------------------------------- the gap: bracket + pill with the change
const bt = win(0.62, 0.82);
if (bt > 0) {
  // last year's mark drops onto this quarter's bar as a dashed line; the part of the bar beyond it
  // (the change) gets a bright edge, with the rupiah change pill sitting just above it
  const xa = M + A.full, xb = M + B.full, e = ease(bt), lo = Math.min(xa, xb), hi2 = Math.max(xa, xb);
  const yTop = y1 + bh + 3, yBot = yTop + (y2 - 1 - yTop) * e;
  mk("line", { x1: xa, y1: yTop, x2: xa, y2: yBot, class: "nf",
    style: `stroke:${TONE.hi};stroke-width:1.3px;stroke-dasharray:3 3;opacity:0.85` }, svg);
  // the change span: a bracket hugging the top of the new bar, from the mark to the bar's end
  const sx = lo + (hi2 - lo) * (1 - e) * (xb >= xa ? 0 : 1), ex = xb >= xa ? lo + (hi2 - lo) * e : hi2;
  const yb = y2 - 5;
  mk("path", { d: `M${sx} ${yb + 4}V${yb}H${ex}V${yb + 4}`, class: "nf", style: `stroke:${INK};stroke-width:1.6px` }, svg);
  const diff = now.v - yago.v, [div, u] = unitOf(diff);
  const txt = `${diff >= 0 ? "+" : "−"}Rp ${(Math.abs(diff) * e / div).toFixed(1)} ${u}`, pw = txt.length * 5.6 + 18;
  const ym = yb - 14, px = Math.max(M, Math.min(W - M - pw, (lo + hi2) / 2 - pw / 2)), pg = mk("g", { opacity: e }, svg);
  mk("rect", { x: px, y: ym - 9, width: pw, height: 18, rx: 9, style: "fill:var(--acc);stroke:none" }, pg);
  type(pg, px + pw / 2, ym + 3.6, txt, "label", { fill: TONE.ground, size: 9, weight: 800, anchor: "middle" });
}

// ---------------------------------------------------------------- the last 8 quarters, landing one by one
// the two quarters in focus are solid (same colours as the bars above) with their values;
// the rest are dotted outlines for context, each with its quarter underneath
const q = ser.slice(-8), sy = H - 64, sw = (W - 2 * M) / q.length, smax = Math.max(...q.map((p) => Math.max(0, p.v)));
const st = win(0.7, 1), short = (l) => l.replace(/^(Q\d)[- ]\d\d(\d\d)$/, "$1 '$2");
type(mk("g", { opacity: ease(Math.min(1, st * 3)) }, svg), M, sy - 54, "LAST 8 QUARTERS", "caps", { fill: TONE.faint, size: 5.6 });
q.forEach((p, i) => {
  const lt = ease(Math.max(0, Math.min(1, st * 1.8 - i * 0.1)));
  if (lt <= 0) return;
  const last = p === now, focus = last || p === yago;
  const hh = Math.max(2, 32 * (Math.max(0, p.v) / smax)) * lt, x = M + i * sw + 5, bw = sw - 10, cx = x + bw / 2;
  if (last && lt > 0.9) glow(cx, sy - hh / 2, 26, 30, 0.35);
  mk("rect", focus
    ? { x, y: sy - hh, width: bw, height: hh, rx: 2, style: `fill:${last ? FILL : TONE.mid};stroke:none` }
    : { x: x + 0.5, y: sy - hh + 0.5, width: bw - 1, height: Math.max(1, hh - 1), rx: 2, class: "nf",
        style: `fill:none;stroke:${TONE.faint};stroke-width:1px;stroke-dasharray:2 2` }, svg);
  const lg = mk("g", { opacity: lt }, svg);
  type(lg, cx, sy + 10, short(p.label), "label", { fill: last ? INK : focus ? TONE.hi : TONE.faint, size: 6.2, weight: focus ? 750 : 500, anchor: "middle" });
  if (focus) {
    const [div, u] = unitOf(p.v), num = p.v / div;
    type(lg, cx, sy - hh - 4, `${num >= 100 ? num.toFixed(0) : num.toFixed(1)}${u}`, "label", { fill: last ? INK : TONE.hi, size: 6.6, weight: 750, anchor: "middle" });
  }
});
mk("line", { x1: M, y1: sy, x2: W - M, y2: sy, class: "lo thin" }, svg);
grain(0.08);
