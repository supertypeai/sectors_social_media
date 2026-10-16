// Insider "story of the deal", slide 4: what the price says. The deal price, the market close that day and
// today's price as bars from Rp 0; the gap as one number; then the whole company valued at each.
// DATA.slide: { title, accent[], bars: [{l, v, acc?}], gap, sinceDeal, impliedTxt, marketTxt, implied, market, name, note }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title", { accent: S.accent, maxW: W - 2 * M });

// ---------------------------------------------------------------- the gap, as one number
const GY = y + 58;
const sign = S.gap < 0 ? "−" : "+";
const gapRun = typeRun(svg, M - 2, GY, [[`${sign}${Math.abs(S.gap)}`, 52, 240, TONE.hi], ["%", 22, 300, TONE.muted]]);
const gw = gapRun.getBBox().width;
type(svg, M + gw + 8, GY - 20, "vs the market", "label", { fill: TONE.hi, size: 9.5, weight: 600 });
type(svg, M + gw + 8, GY - 8, "close that day", "label", { fill: TONE.muted, size: 9 });

// ---------------------------------------------------------------- three prices from Rp 0
let by = GY + 34;
const bx0 = M, bx1 = W - M - 64, vmax = Math.max(...S.bars.map((b) => b.v));
const bs = scale(0, vmax, bx0, bx1);
S.bars.forEach((b, i) => {
  const ry = by + i * 28;
  type(svg, bx0, ry - 5, b.l, "label", { fill: b.acc ? "var(--acc)" : TONE.muted, size: 7.2, weight: b.acc ? 650 : 500 });
  mk("rect", { x: bx0, y: ry, width: Math.max(2, bs(b.v) - bx0), height: 9, rx: 2, style: `fill:${b.acc ? "var(--acc)" : i === 1 ? TONE.edge : TONE.mid};stroke:none` }, svg);
  type(svg, bs(b.v) + 6, ry + 8, rp(b.v), "label", { size: 10, weight: 650, fill: b.acc ? "var(--acc)" : TONE.hi });
});
by += S.bars.length * 28 + 4;
if (S.sinceDeal !== 0) type(svg, bx0, by, `Since the deal day the market price has moved ${S.sinceDeal > 0 ? "+" : "−"}${Math.abs(S.sinceDeal)}%.`, "label", { fill: TONE.faint, size: 7 });
else type(svg, bx0, by, "The market price today is where it closed on the deal day.", "label", { fill: TONE.faint, size: 7 });

// ---------------------------------------------------------------- the whole company, valued at each
if (S.implied) {
  const VY = by + 30;
  mk("line", { x1: M, y1: VY - 14, x2: W - M, y2: VY - 14, class: "lo thin" }, svg);
  type(svg, M, VY, `All of ${S.name}, valued at`, "caps", { fill: TONE.muted });
  const half = (W - 2 * M) / 2;
  [[S.impliedTxt, "the deal price", true], [S.marketTxt, "the market close", false]].forEach(([v, l, acc], i) => {
    const x = M + i * half;
    if (i) mk("line", { x1: x - 8, y1: VY + 10, x2: x - 8, y2: VY + 42, class: "lo thin" }, svg);
    type(svg, x, VY + 30, v, "num", { size: 24, weight: 280, fill: TONE.hi });
    type(svg, x, VY + 43, l, "label", { fill: TONE.muted, size: 6.8 });
  });
  by = VY + 50;
}

// ---------------------------------------------------------------- the plain reading
mk("line", { x1: M, y1: by + 10, x2: W - M, y2: by + 10, class: "lo thin" }, svg);
wrapText(S.note, 9.4, W - 2 * M).forEach((l, i) => type(svg, M, by + 28 + i * 12.5, l, "body", { size: 9.4, fill: TONE.muted }));
grain(0.05);
