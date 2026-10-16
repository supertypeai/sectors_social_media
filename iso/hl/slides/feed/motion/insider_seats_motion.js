// Insider cover, animated (seats). The words are set from frame 1; only the seats and the counters move.
// PROG 0 → 1:
//   0.00–0.30  the 100 seats appear row by row, as they were BEFORE the deal
//                sell: the holder's seats lit; change of hands: the SELLER's seats in grey; buy: holder's old seats
//   0.30–0.85  the move, seat by seat, in order:
//                sell: the holder's sold seats go out to dashed rings
//                change of hands: the seller's grey seats turn the buyer's colour, one by one, from the first
//                plain buy: empty seats light up
//              and every stake counter rolls from its old value to its new one (up when it grew, down when it fell)
//   0.85–1.00  the deal value settles; the last frame is the still cover
// DATA.slide: { holder{name,sym,logo,initials}, other?{name}, headline, accent[], sym, before, after, sell,
//               otherBefore?, otherAfter?, value, span, year }
const D = DATA, S = D.slide;
setAccent(D.direction);
const P = typeof PROG === "number" ? PROG : 1;
const win = (a, b) => Math.max(0, Math.min(1, (P - a) / (b - a)));
const ease = (t) => (t < 0.5 ? 4 * t * t * t : 1 - Math.pow(-2 * t + 2, 3) / 2);
frame(D);
grain(0.05);

// ---------------------------------------------------------------- the words (static)
const badge = (cx, cy, r, b) => {
  if (b.logo) return logoChip(svg, cx, cy, r, b.logo, b.sym);
  mk("circle", { cx, cy, r, style: `fill:${TONE.card};stroke:var(--acc);stroke-width:1.1px` }, svg);
  type(svg, cx, cy + r * 0.34, b.initials, "label", { size: r * 0.9, weight: 600, anchor: "middle", fill: TONE.hi });
};
const swap = !!S.other, role = swap || !S.sell ? "THE BUYER" : "THE SELLER";
badge(M + 13, 66, 13, S.holder);
type(svg, M + 34, 63, role, "caps", { fill: "var(--acc)", weight: 750 });
type(svg, M + 34, 74, S.holder.sym ? `Listed as ${S.holder.sym}` : "Insider of " + S.sym, "label", { fill: TONE.muted, size: 7 });
let size = S.other ? 38 : 46, lines; // a change of hands needs more room below for both counters
for (; size > 26; size -= 2) {
  lines = wrapText(S.holder.name, size, W - 2 * M, 0.5);
  if (lines.length <= 2 && Math.max(...lines.map((l) => l.length)) * size * 0.5 <= W - 2 * M) break;
}
let y = 96 + size * 0.85;
for (const l of lines) { type(svg, M - 2, y, l, "hero", { size, weight: 330 }); y += size * 0.98; }
y += 4 - size * 0.38; // the headline sits right under the name, not a full line below
for (const l of wrapText(S.headline, 16, W - 2 * M, 0.47)) {
  const t = type(svg, M, y, "", "title", { size: 16, weight: 500 });
  t.innerHTML = l.split(" ").map((w) => S.accent.includes(w) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
  y += 16 * 1.18;
}
y += 10;

// ---------------------------------------------------------------- the seats: a before state and an after state
const R = (v) => Math.round(v);
const before = [], after = [];
if (swap) {
  // the seller's seats come first; the first nNew of them change hands
  const nSel = R(S.otherBefore), nNew = R(S.after), nOld = R(S.before);
  for (let i = 0; i < nOld; i++) { before.push("acc"); after.push("acc"); }
  for (let i = 0; i < nSel; i++) { before.push("seller"); after.push(i < nNew ? "acc" : "seller"); }
} else if (S.sell) {
  const nWas = R(S.before), nNow = R(S.after);
  for (let i = 0; i < nWas; i++) { before.push("acc"); after.push(i < nNow ? "acc" : "gone"); }
} else {
  const nWas = R(S.before), nNow = R(S.after);
  for (let i = 0; i < nNow; i++) { before.push(i < nWas ? "acc" : "rest"); after.push("acc"); }
}
while (before.length < 100) { before.push("rest"); after.push("rest"); }
// the order the seats change in: the changing ones, from the end of the holder's block (sell) or the start (buy)
const changing = before.map((k, i) => (k !== after[i] ? i : -1)).filter((i) => i >= 0);
if (S.sell && !swap) changing.reverse();
const look = {
  acc: "fill:var(--acc);stroke:none",
  seller: `fill:${TONE.edge};stroke:none`,
  gone: "fill:none;stroke:var(--acc);stroke-width:.9px;stroke-dasharray:1.6 1.4",
  rest: `fill:${TONE.lo};stroke:none`,
};
// leave room under the grid for the deal value, its description and the footer
const step = Math.min(14.5, (418 - 52 - y) / 10), r = step * 0.36, gx = M + r + 1, gy = y + r;
const appear = win(0, 0.3), mt = win(0.3, 0.85);
before.slice(0, 100).forEach((k0, i) => {
  const row = Math.floor(i / 10), a = ease(Math.max(0, Math.min(1, appear * 11 - row)));
  if (a <= 0) return;
  const ci = changing.indexOf(i);
  // each changing seat has its own short window inside the move, one after another
  const local = ci < 0 ? 0 : Math.max(0, Math.min(1, mt * (changing.length + 6) / 7 - ci / 7));
  const cx = gx + (i % 10) * step, cy = gy + row * step;
  if (ci < 0 || local <= 0) { mk("circle", { cx, cy, r: r * (0.6 + 0.4 * a), style: look[k0], opacity: a }, svg); return; }
  const k1 = after[i], e = ease(local);
  // cross-fade old → new with a small pop at the swap
  mk("circle", { cx, cy, r, style: look[k0], opacity: 1 - e }, svg);
  mk("circle", { cx, cy, r: r * (1 + 0.35 * Math.sin(Math.PI * e)), style: look[k1], opacity: e }, svg);
});

// ---------------------------------------------------------------- the counters: roll up or down
const lx = gx + 10 * step + 10;
// the key sits under the dot grid
type(mk("g", { opacity: ease(win(0.05, 0.25)) }, svg), gx - r, gy + 9 * step + r + 14, `1 dot = 1% of ${S.sym}`, "caps", { fill: TONE.faint, size: 5.8 });
/** NumberFlow-style digits (number-flow.barvian.me): each digit is its own wheel that spins to the new digit,
 *  upward when the number grows and downward when it falls, rightmost digits a beat later; digits leaving the
 *  line fade out as they roll away; a digit that only exists on one side fades/scales in or out.
 *  Draws `a` → `b` at progress t, left-aligned at (x, y); returns the width of the final number. */
function numberFlow(g, x, y, a, b, t, size, color, decimals = 2) {
  const A = a.toFixed(decimals), B = b.toFixed(decimals), n = Math.max(A.length, B.length);
  const pa = A.padStart(n, " "), pb = B.padStart(n, " "), up = b >= a;
  const cw = size * 0.6, dot = size * 0.3, lh = size * 0.95;
  const wOf = (c) => (c === "." ? dot : c === " " ? 0 : cw);
  // each slot's local progress (staggered, rightmost a beat later) and eased value
  const prog = [...pb].map((_, i) => { const lt = Math.max(0, Math.min(1, (t - (i / n) * 0.3) / 0.7)); return lt < 0.5 ? 4 * lt ** 3 : 1 - (-2 * lt + 2) ** 3 / 2; });
  // widths animate: a digit that appears grows its slot from 0, one that leaves shrinks it to 0
  const widths = [...pb].map((c, i) => wOf(pa[i]) + (wOf(c) - wOf(pa[i])) * prog[i]);
  const total = widths.reduce((s, v) => s + v, 0), maxW = Math.max(...[pa, pb].map((s) => [...s].reduce((q, c) => q + wOf(c), 0)));
  // a soft mask one line tall around the digits (like NumberFlow's): rolling digits fade at its top and bottom
  // edges and never reach text above or below
  const id = `nf${Math.round(x)}${Math.round(y)}`, defs = mk("defs", {}, g);
  const lgd = mk("linearGradient", { id: `${id}g`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  [[0, 0], [0.22, 1], [0.82, 1], [1, 0]].forEach(([o, a2]) => mk("stop", { offset: o, "stop-color": "#fff", "stop-opacity": a2 }, lgd));
  const mask = mk("mask", { id, maskUnits: "userSpaceOnUse", x: x - 4, y: y - size * 0.98, width: maxW + 8, height: size * 1.25 }, defs);
  mk("rect", { x: x - 4, y: y - size * 0.98, width: maxW + 8, height: size * 1.25, style: `fill:url(#${id}g);stroke:none` }, mask);
  const host = g;
  g = mk("g", { mask: `url(#${id})` }, host);
  let cx = x;
  for (let i = 0; i < n; i++) {
    let ca = pa[i], cb = pb[i];
    const wi = widths[i], e = prog[i];
    // a digit that appears spins in from 0 (and one that leaves spins out to 0), so it counts rather than pops
    if (ca === " " && /\d/.test(cb)) ca = "0";
    if (cb === " " && /\d/.test(ca)) cb = "0";
    const fadeSlot = pa[i] === " " ? e : pb[i] === " " ? 1 - e : 1;
    const put = (ch, dy, op, sc = 1) => {
      op *= fadeSlot;
      if (op <= 0.01 || ch === " ") return;
      const tt = type(g, cx + wi / 2, y + dy, ch, "num", { size, weight: 400, fill: color, anchor: "middle" });
      tt.setAttribute("opacity", op.toFixed(3));
      if (sc !== 1) tt.setAttribute("transform", `translate(${cx + wi / 2} ${y + dy}) scale(${sc}) translate(${-(cx + wi / 2)} ${-(y + dy)})`);
    };
    if (/\d/.test(ca) && /\d/.test(cb) && ca !== cb) {
      const da = +ca, db = +cb, steps = up ? (db - da + 10) % 10 : (da - db + 10) % 10;
      const pos = steps * e, k = Math.floor(pos), f = pos - k, dir = up ? -1 : 1;
      // the digit leaving and the digit arriving, each faded by how far it sits from the line
      const d1 = (up ? da + k : da - k + 10) % 10, d2 = (up ? da + k + 1 : da - k - 1 + 20) % 10;
      put(String(d1), dir * lh * f, 1 - f);
      if (f > 0) put(String(d2), -dir * lh * (1 - f), f);
    } else if (ca === cb) {
      put(cb, 0, 1);
    }
    cx += wi;
  }
  return total;
}

/** A stake that rolls from `a` to `b`: the old value slides out and the new one slides in, upward when the
 *  stake grew and downward when it fell, inside a clipped line. */
let rid = 0;
function roller(x, yy, label, a, b, t, color, chip = true, size = 26) {
  // the label and the starting value slide in with the seats; then the value rolls (a short slide + cross-fade,
  // small enough never to reach the label above it)
  const ia = ease(win(0.12, 0.32)), lg = mk("g", { opacity: ia, transform: `translate(0 ${(1 - ia) * 8})` }, svg);
  type(lg, x, yy - size - 4, label, "caps", { fill: TONE.muted, size: 5.8, weight: 750 });
  const up = b >= a, g = mk("g", { opacity: ia }, svg);
  const w = numberFlow(g, x, yy, a, b, t, size, color);
  type(g, x + w + 1, yy, "%", "label", { size: size * 0.46, fill: TONE.muted });
  // the change beside it, like a price ticker (+5.64%): counts up with the move, in green or terracotta
  if (chip && t > 0) {
    const d = (b - a) * ease(t), cg = mk("g", { opacity: ease(Math.min(1, t * 3)) }, svg);
    // a big number leaves no room beside it: the change goes underneath instead
    const big = size > 30;
    type(cg, big ? x + 1 : x + w + 14, big ? yy + 18 : yy - 2, `${d >= 0 ? "+" : "−"}${Math.abs(d).toFixed(2)} pts`, "label", { fill: up ? "#b2d2b9" : "#dc8d74", size: 10, weight: 700 });
  }
}
if (swap) {
  const sName = S.other.name.split(" ").slice(0, 2).join(" "), bName = S.holder.name.split(" ").slice(0, 2).join(" ");
  // both roll while the seats move across: the seller's stake down a beat ahead, the buyer's up right after it
  // one change, two sides: instead of the same ±pts twice, a single "moved" chip travels from the seller's line
  // down to the buyer's, carrying the stake, while both numbers count
  roller(lx, gy + 28, sName.toUpperCase(), S.otherBefore, S.otherAfter, win(0.38, 0.78), TONE.hi, false);
  roller(lx, gy + 114, bName.toUpperCase(), S.before, S.after, win(0.45, 0.85), "var(--acc)", false);
  const mv = (S.after - S.before), tt = ease(win(0.38, 0.85)), ax = lx + 8, ay0 = gy + 38, ay1 = gy + 58;
  const ag = mk("g", { opacity: ease(win(0.3, 0.42)) }, svg);
  mk("path", { d: `M${ax} ${ay0}V${ay1}`, class: "nf", style: `stroke:${TONE.mid};stroke-width:1px;stroke-dasharray:2 2` }, ag);
  mk("path", { d: `M${ax} ${ay0}V${ay0 + (ay1 - ay0) * tt}`, class: "nf", style: "stroke:var(--acc);stroke-width:1.6px" }, ag);
  mk("path", { d: `M${ax - 4} ${ay1 - 4}L${ax} ${ay1}L${ax + 4} ${ay1 - 4}`, class: "nf", style: `stroke:${tt > 0.95 ? "var(--acc)" : TONE.mid};stroke-width:1.4px` }, ag);
  const py = ay0 + (ay1 - ay0) * tt - 7, txt = `${(mv * tt).toFixed(2)}% changed hands`, pw = txt.length * 4.4 + 14;
  mk("rect", { x: ax + 10, y: py, width: pw, height: 14, rx: 7, style: "fill:var(--acc);stroke:none" }, ag);
  type(ag, ax + 10 + pw / 2, py + 9.6, txt, "label", { fill: TONE.ground, size: 7, weight: 750, anchor: "middle" });
} else {
  roller(lx, gy + 50, "STAKE", S.before, S.after, win(0.4, 0.85), "var(--acc)", true, 42);
}
const fe = ease(win(0.85, 1)), fg = mk("g", { opacity: fe, transform: `translate(0 ${(1 - fe) * 8})` }, svg), by = Math.min(H - 76, Math.max(gy + 9 * step + r, gy + (swap ? 136 : 84)));
// the separator sits clear of the last counter above it and of the value below it
mk("line", { x1: lx, y1: by - 4, x2: W - M, y2: by - 4, class: "lo thin" }, fg);
typeRun(fg, lx, by + 24, [[S.value, 15, 400, "var(--acc)"]]);
type(fg, lx, by + 37, swap ? "total deal value" : S.sell ? "total value sold" : "total value bought", "label", { size: 7, fill: TONE.muted });
type(fg, W - M, by + 24, `${S.span} ${S.year}`, "label", { size: 7, fill: TONE.muted, anchor: "end" });
type(fg, W - M, by + 37, "trade date", "label", { size: 7, fill: TONE.faint, anchor: "end" });
