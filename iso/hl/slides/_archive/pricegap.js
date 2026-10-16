// Style E, the price gap: the sale price and that day's market close on one scale from zero, so the
// distance between them is the story. The hero is the discount.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

const gap = (S.salePrice / S.close - 1) * 100; // signed: below the close is negative
typeRun(svg, M - 4, 150, [[`${gap < 0 ? "−" : "+"}${Math.abs(gap).toFixed(0)}`, 110, 200, "var(--acc)"], ["%", 46, 230, TONE.muted]]);
para(svg, M, 186, `${S.holder} ${S.verb ?? "sold"} ${S.value} of ${S.company ?? "the company"} ${gap < 0 ? "below" : "above"} the market price that day`, "title", { accent: S.accent });

// one scale, Rp 0 to the close (plus air): two levels, the gap between them shaded
const X0 = M, X1 = W - M, xs = scale(0, S.close * 1.08, X0, X1), Y = 320;
mk("line", { x1: X0, y1: Y, x2: X1, y2: Y, class: "lo" }, svg);
mk("rect", { x: xs(S.salePrice), y: Y - 3, width: xs(S.close) - xs(S.salePrice), height: 6, style: "fill:var(--acc);fill-opacity:.22;stroke:none" }, svg);
mk("rect", { x: X0, y: Y - 3, width: xs(S.salePrice) - X0, height: 6, style: `fill:${TONE.hi};stroke:none` }, svg);
for (const [v, head, sub, below, fill] of [
  [S.salePrice, `Rp ${S.salePrice.toLocaleString("en-US")}`, `${S.verb === "bought" ? "buy" : "sale"} price · ${S.shares}`, true, "var(--acc)"],
  [S.close, `Rp ${S.close.toLocaleString("en-US")}`, `market close, ${S.tradeDay}`, false, TONE.hi],
]) {
  const x = xs(v);
  mk("line", { x1: x, y1: Y - 14, x2: x, y2: Y + 14, style: `stroke:${fill === TONE.hi ? TONE.hi : "var(--acc)"};stroke-width:1.6px` }, svg);
  const anchor = x > W * 0.7 ? "end" : "start";
  type(svg, x, below ? Y + 36 : Y - 30, head, "num", { size: 22, weight: 300, fill, anchor });
  type(svg, x, below ? Y + 48 : Y - 19, sub, "label", { size: 7, fill: TONE.muted, anchor });
}
type(svg, X0, Y + 10, "Rp 0", "label", { size: 6.4, fill: TONE.faint });
type(svg, M, 404, `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}%`, "body", { fill: TONE.muted, size: 8 });
