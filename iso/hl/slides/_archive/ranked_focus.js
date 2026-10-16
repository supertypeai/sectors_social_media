// A ranked list with one focal point, in the Sectors Hairline style. Top: the hero (one big number and
// the finding in one sentence). Below: the list as quiet context, logo + ticker + hairline bar + value;
// only the row the hero is about (`hi`) is in the accent. Bars are true to scale and may go negative.
// DATA.slide: { hero: { num, unit }, title, accent[], line, rows: [{ sym, logo, label, value, display, hi }] }.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

// the hero
// the hero numeral shrinks for long values ("Rp 26.5 T") so it always fits the width
const heroSize = Math.min(88, (W - 2 * M) / ((S.hero.num.length + (S.hero.unit ? 0.6 : 0)) * 0.56));
typeRun(svg, M - 3, 124, [[S.hero.num, heroSize, 220, "var(--acc)"], [S.hero.unit ?? "", heroSize * 0.39, 260, TONE.muted]]);
let y = para(svg, M, 156, S.title, "title", { accent: S.accent ?? [] });
type(svg, M, y + 17, S.line, "body", { fill: TONE.muted });

// the list
const rows = S.rows, TOP = y + 44, BOTTOM = H - 46, RH = Math.min(30, (BOTTOM - TOP) / rows.length);
const vals = rows.map((r) => r.value), neg = vals.some((v) => v < 0);
const maxAbs = Math.max(...vals.map(Math.abs));
const BX0 = M + 118, BX1 = W - M - 52; // bar area, leaving room for the value on the right
const zero = neg ? BX0 + (BX1 - BX0) * (Math.max(0, -Math.min(...vals)) / (Math.max(...vals, 0) - Math.min(...vals, 0))) : BX0;
const scaleX = (v) => (Math.abs(v) / maxAbs) * (neg ? Math.max(zero - BX0, BX1 - zero) : BX1 - BX0);
const defs = mk("defs", {}, svg);
if (neg) mk("line", { x1: zero, y1: TOP - 4, x2: zero, y2: TOP + RH * rows.length - 6, class: "lo thin" }, svg);

rows.forEach((r, i) => {
  const cy = TOP + i * RH + RH / 2, g = mk("g", {}, svg), hi = !!r.hi;
  // logo in a small circle (white disc so dark logos read), then the ticker and its label
  const cid = `lc${i}`, LR = 8;
  const cp = mk("clipPath", { id: cid }, defs);
  mk("circle", { cx: M + LR, cy, r: LR }, cp);
  mk("circle", { cx: M + LR, cy, r: LR + 0.6, style: `fill:#f2efe9;stroke:${hi ? "var(--acc)" : "none"};stroke-width:1.2px` }, g);
  if (r.logo) mk("image", { href: r.logo, x: M + 1.5, y: cy - LR + 1.5, width: 2 * LR - 3, height: 2 * LR - 3, "clip-path": `url(#${cid})`, preserveAspectRatio: "xMidYMid meet" }, g);
  type(g, M + 22, cy + 1, r.sym, "label", { size: 9, weight: 700, fill: hi ? TONE.hi : TONE.muted });
  if (r.label) type(g, M + 22, cy + 8.6, r.label, "label", { size: 5.6, fill: TONE.faint });
  // the bar: a rounded hairline, filled faintly; the hero's in the accent
  const len = Math.max(1.5, scaleX(r.value)), x0 = r.value >= 0 ? zero : zero - len;
  mk("rect", { x: x0, y: cy - 3, width: len, height: 6, rx: 3, style: hi ? "fill:var(--acc);fill-opacity:.85;stroke:none" : `fill:${TONE.mid};stroke:none` }, g);
  const vx = r.value >= 0 ? x0 + len + 5 : x0 - 5;
  type(g, neg ? vx : BX1 + 50, cy + 3, r.display, "label", { size: 8.6, weight: hi ? 700 : 550, anchor: neg ? (r.value >= 0 ? "start" : "end") : "end", fill: hi ? "var(--acc)" : TONE.hi });
});
