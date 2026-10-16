// Insider "story of the deal", slide 2: who is this holder? What kind of holder, how often they file, what
// else they own in listed companies, and every filing on record as a tape (one row per stock, the move glowing).
// DATA.slide: { title, whoLine, listedSym, listedLogo, stats: [{v, l}], holdings: [{sym, pct, this?, logo}],
//               tape: [{sym, date, buy, value, move}], moveDate }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title", { maxW: W - 2 * M });
if (S.listedSym) {
  const t = type(svg, M, y + 22, "A listed company, trading as", "body", { fill: TONE.muted, size: 9.5 });
  tickerChip(svg, M + t.getBBox().width + 6, y + 22, S.listedSym, S.listedLogo, { size: 9 });
} else type(svg, M, y + 22, S.whoLine, "body", { fill: TONE.muted, size: 9.5 });

// ---------------------------------------------------------------- the record in three numbers
// buys are green and sells red everywhere on this slide, whatever the post's own colour
const BUY = "#81a789", BUY_INK = "#b2d2b9", SELL = "#c07159", SELL_INK = "#dc8d74";
const SY = y + 64, cw = (W - 2 * M) / 3;
S.stats.forEach((f, i) => {
  const x = M + i * cw;
  if (i) mk("line", { x1: x - 8, y1: SY - 20, x2: x - 8, y2: SY + 12, class: "lo thin" }, svg);
  const bs = /buys/.test(f.l) && String(f.v).match(/^(\d+)\s*\/\s*(\d+)$/);
  if (bs) typeRun(svg, x, SY, [[bs[1], 24, 280, BUY_INK], [" / ", 24, 200, TONE.faint], [bs[2], 24, 280, SELL_INK]]);
  else type(svg, x, SY, f.v, "num", { size: 24, weight: 280 });
  type(svg, x, SY + 13, f.l, "label", { fill: TONE.muted, size: 6.6 });
});

// ---------------------------------------------------------------- what they own (company reports)
let hy = SY + 42;
mk("line", { x1: M, y1: hy - 12, x2: W - M, y2: hy - 12, class: "lo thin" }, svg);
type(svg, M, hy, "Stakes in listed companies", "caps", { fill: TONE.muted });
hy += 18;
const bx0 = M + 62, bx1 = W - M - 46, top = Math.max(60, ...S.holdings.map((h) => h.pct));
const bs = scale(0, top, bx0, bx1);
S.holdings.forEach((h, i) => {
  const ry = hy + i * 27;
  tickerChip(svg, M, ry + 3, h.sym, h.logo, { size: 8.4, fill: h.this ? TONE.hi : TONE.hi });
  mk("rect", { x: bx0, y: ry - 4, width: bx1 - bx0, height: 6, rx: 3, style: `fill:${TONE.lo};stroke:none` }, svg);
  if (h.pct > 0) mk("rect", { x: bx0, y: ry - 4, width: Math.max(3, bs(h.pct) - bx0), height: 6, rx: 3, style: `fill:${h.this ? "var(--acc)" : TONE.edge};stroke:none` }, svg);
  type(svg, W - M, ry + 2.5, `${h.pct.toFixed(h.pct >= 10 ? 1 : 2)}%`, "label", { size: 9, weight: 650, anchor: "end", fill: h.this ? "var(--acc)" : TONE.hi });
  if (h.this) type(svg, bx0, ry + 12, "after this deal", "label", { fill: TONE.faint, size: 6.2 });
});
hy += S.holdings.length * 27;

// ---------------------------------------------------------------- every filing on record
const TY = hy + 26;
mk("line", { x1: M, y1: TY - 12, x2: W - M, y2: TY - 12, class: "lo thin" }, svg);
type(svg, M, TY, "Every filing on record", "caps", { fill: TONE.muted });
// the key, at the right
const kx = W - M;
type(svg, kx, TY, "sold", "label", { fill: SELL_INK, size: 6.6, weight: 650, anchor: "end" });
mk("circle", { cx: kx - 18, cy: TY - 2.2, r: 2.6, style: `fill:${SELL};stroke:none` }, svg);
type(svg, kx - 27, TY, "bought", "label", { fill: BUY_INK, size: 6.6, weight: 650, anchor: "end" });
mk("circle", { cx: kx - 54, cy: TY - 2.2, r: 2.6, style: `fill:${BUY};stroke:none` }, svg);

const syms = [...new Set(S.tape.map((t) => t.sym))].slice(0, 3);
const ts = S.tape.map((t) => dayOf(t.date));
const t0 = Math.min(...ts) - 864e5 * 20, t1 = Math.max(Date.now(), Math.max(...ts)) + 864e5 * 5;
const xs = scale(t0, t1, M + 40, W - M - 14), vmax = Math.max(...S.tape.map((t) => t.value));
const rr = (v) => 2.2 + 6 * Math.sqrt(v / vmax);
// a short rupiah value over each dot (Rp 850 M · Rp 59 B · Rp 1.2 T)
const short = (v) => v >= 1e12 ? `Rp ${(v / 1e12).toFixed(1)} T` : v >= 1e9 ? `Rp ${(v / 1e9).toFixed(v >= 1e11 ? 0 : 1)} B` : `Rp ${Math.round(v / 1e6)} M`;
const rowH = 36, ry0 = TY + 32;
syms.forEach((s, i) => {
  const ry = ry0 + i * rowH;
  type(svg, M, ry + 3, s, "label", { size: 8, weight: 700, fill: TONE.hi });
  mk("line", { x1: M + 40, y1: ry, x2: W - M, y2: ry, class: "lo thin" }, svg);
  const g = mk("g", {}, svg);
  const row = S.tape.filter((t) => t.sym === s).sort((a, b) => dayOf(a.date) - dayOf(b.date));
  // the other filings: solid dots in their colour, a little faded; values only where they have room
  const move = row.find((t) => t.move), mx = move ? xs(dayOf(move.date)) : null;
  const rest = row.filter((t) => !t.move);
  rest.forEach((t) => mk("circle", { cx: xs(dayOf(t.date)), cy: ry, r: rr(t.value), style: `fill:${t.buy ? BUY : SELL};fill-opacity:.7;stroke:${TONE.ground};stroke-width:.6px` }, g));
  // biggest trades get their value first; a label is skipped if it would crowd one already placed
  const placed = mx === null ? [] : [mx];
  [...rest].sort((a, b) => b.value - a.value).forEach((t) => {
    const x = xs(dayOf(t.date));
    if (placed.some((p) => Math.abs(p - x) < (p === mx ? 44 : 30))) return;
    type(g, x, ry - rr(t.value) - 4, short(t.value), "label", { fill: TONE.muted, size: 5.6, anchor: "middle" });
    placed.push(x);
  });
  // this deal: bigger, glowing, with what happened spelled out above it
  if (move) {
    const c = move.buy ? BUY : SELL, r = Math.max(4.5, Math.min(6.5, rr(move.value)));
    glowDot(g, mx, ry, c, r);
    type(g, Math.min(mx, W - M - 2), ry - r * 3 - 3, `${move.buy ? "bought" : "sold"} ${short(move.value)}`, "label",
      { fill: move.buy ? BUY_INK : SELL_INK, size: 7, weight: 750, anchor: mx > W - M - 40 ? "end" : "middle" });
  }
});
// time ends under the tape
const ay = ry0 + (syms.length - 1) * rowH + 20;
type(svg, M + 40, ay, fmtMonth(t0 + 864e5 * 20) + " " + new Date(t0 + 864e5 * 20).getUTCFullYear(), "label", { fill: TONE.faint, size: 6.4 });
type(svg, W - M, ay, "now", "label", { fill: TONE.faint, size: 6.4, anchor: "end" });
if (S.tape.length <= 1) type(svg, M + 40, ay + 12, "This deal is the first filing on record under this name.", "label", { fill: TONE.muted, size: 7 });
else type(svg, M + 40, ay + 12, "Bigger dot, bigger trade. The glowing one is this filing.", "label", { fill: TONE.faint, size: 6.6 });
grain(0.05);
