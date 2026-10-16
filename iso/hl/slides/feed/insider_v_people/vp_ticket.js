// Insider "people", slide 2: the deal as a receipt. Who handed shares to whom, when, how many, at what price,
// and how that price compares with the market's close on the day. Answers "what exactly happened?"
// DATA.slide: { holder, other?, sell, sym, name, span, year, shares, price, value, close?, gap?, before, after,
//               otherBefore?, otherAfter?, legs[{date, price, shares}], nLegs, filed }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

para(svg, M, 74, "The deal, on paper", "title", {});
type(svg, M, 90, `What the filing to IDX says, filed ${S.filed}.`, "body", { fill: TONE.muted });

const paper = mk("g", {}, svg); // drawn last, sized to the content, but sits behind it
function badge(cx, cy, r, b) {
  if (!b) { // the other side wasn't named in any filing
    mk("circle", { cx, cy, r, style: `fill:none;stroke:${TONE.edge};stroke-width:1px;stroke-dasharray:2 2` }, svg);
    type(svg, cx, cy + r * 0.32, "?", "label", { size: r * 0.95, weight: 500, anchor: "middle", fill: TONE.muted });
    return;
  }
  if (b.logo) { logoChip(svg, cx, cy, r, b.logo, b.sym); return; }
  mk("circle", { cx, cy, r, style: `fill:${TONE.card};stroke:var(--acc);stroke-width:1.1px` }, svg);
  type(svg, cx, cy + r * 0.34, b.initials, "label", { size: r * 0.9, weight: 600, anchor: "middle", fill: TONE.hi });
}

const X0 = M + 6, X1 = W - M - 6, Y0 = 108;
// ---------------------------------------------------------------- from → to
const sellerB = S.sell ? S.holder : S.other, buyerB = S.sell ? S.other : S.holder;
const fy = Y0 + 34, ax0 = X0 + 62, ax1 = X1 - 62;
badge(X0 + 36, fy, 17, sellerB);
badge(X1 - 36, fy, 17, buyerB);
mk("path", { d: `M${ax0} ${fy}H${ax1 - 2}`, class: "nf", style: "stroke:var(--acc);stroke-width:1.3px" }, svg);
mk("path", { d: `M${ax1 - 7} ${fy - 4}L${ax1 - 1} ${fy}L${ax1 - 7} ${fy + 4}`, class: "nf", style: "stroke:var(--acc);stroke-width:1.3px" }, svg);
const moved = Math.abs(S.before - S.after);
type(svg, (ax0 + ax1) / 2, fy - 7, `${moved.toFixed(moved >= 10 ? 1 : 2)}% of ${S.sym}`, "label", { size: 11, weight: 650, anchor: "middle", fill: "var(--acc)" });
type(svg, (ax0 + ax1) / 2, fy + 13, S.shares, "label", { size: 7.6, anchor: "middle", fill: TONE.muted });
const who = (cx, b, role) => {
  const lines = wrapText(b ? b.name : "Not named", 7.4, 92, 0.52).slice(0, 2);
  lines.forEach((l, i) => type(svg, cx, fy + 31 + i * 9, l, "label", { size: 7.4, anchor: "middle", weight: 600, fill: b ? TONE.hi : TONE.muted }));
  type(svg, cx, fy + 33 + lines.length * 9, role, "caps", { size: 5.4, anchor: "middle", fill: TONE.faint });
};
who(X0 + 36, sellerB, "SELLER");
who(X1 - 36, buyerB, buyerB ? "BUYER" : "BUYER · NO FILING");

// ---------------------------------------------------------------- the lines of the receipt
let y = fy + 74;
const rule = (yy) => mk("line", { x1: X0 + 12, y1: yy, x2: X1 - 12, y2: yy, style: `stroke:${TONE.mid};stroke-width:.8px;stroke-dasharray:2 2.5` }, svg);
rule(y - 14);
const line = (k, v, { acc = false, big = false } = {}) => {
  type(svg, X0 + 14, y, k, "label", { size: 8.6, fill: TONE.muted });
  type(svg, X1 - 14, y, v, "label", { size: big ? 14 : 9.4, weight: big ? 650 : 600, anchor: "end", fill: acc ? "var(--acc)" : TONE.hi });
  y += big ? 24 : 18;
};
const num = (v) => (Math.abs(v - Math.round(v)) < 0.05 ? Math.round(v).toLocaleString("en-US") : v.toLocaleString("en-US", { maximumFractionDigits: 1 }));
const pc = (v) => `${v.toFixed(2)}%`;
line("Trade date", `${S.span} ${S.year}`);
const sStake = S.sell ? [S.before, S.after] : S.other ? [S.otherBefore, S.otherAfter] : null;
const bStake = S.sell ? (S.other ? [S.otherBefore, S.otherAfter] : null) : [S.before, S.after];
if (sStake) line("Seller's stake", `${pc(sStake[0])} → ${pc(sStake[1])}`);
if (bStake) line("Buyer's stake", `${pc(bStake[0])} → ${pc(bStake[1])}`);
if (S.nLegs > 1) {
  const prices = S.legs.map((l) => l.price), lo = Math.min(...prices), hi = Math.max(...prices);
  line(hi > lo ? `Prices, ${S.nLegs} trades` : `Trades in the filing`, hi > lo ? `Rp ${num(lo)} to Rp ${num(hi)}` : `${S.nLegs}`);
  line("Average price a share", `Rp ${num(S.price)}`);
} else {
  line("Price a share", `Rp ${num(S.price)}`);
}
if (S.close) {
  line(`Market close on ${S.closeDay}`, `Rp ${num(S.close)}`);
  if (S.gap != null) line("Deal price vs that close", `${S.gap >= 0 ? "+" : "−"}${Math.abs(S.gap).toFixed(Math.abs(S.gap) < 10 ? 1 : 0)}%`);
}
rule(y - 7);
y += 14;
line("Total", S.value, { acc: true, big: true });
if (S.gap != null && Math.abs(S.gap) >= 15) {
  y = para(svg, X0 + 14, y - 4, "A price this far from the close usually points to a negotiated block deal, not open-market trading.", "body", { fill: TONE.faint, maxW: X1 - X0 - 28, lh: 1.35 }) + 14;
}
const Y1 = Math.min(y, 404);
{
  // a receipt: square top, a torn (zigzag) bottom edge
  const z = 6, n = Math.round((X1 - X0) / z);
  let d = `M${X0} ${Y0}H${X1}V${Y1}`;
  for (let i = 1; i <= n; i++) d += `L${X1 - i * z + z / 2} ${Y1 + (i % 2 ? 4 : 0)}`;
  d += `L${X0} ${Y1}Z`;
  mk("path", { d, style: `fill:${TONE.card};fill-opacity:.55;stroke:${TONE.mid};stroke-width:1px` }, paper);
}
