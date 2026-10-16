// Review sheet (not a post): all 11 sector icons on one page, as drawn on the earnings peers slide.
const D = DATA;
setAccent(D.direction || "buy");
const names = ["Energy", "Financials", "Basic Materials", "Consumer Non-Cyclicals", "Consumer Cyclicals", "Healthcare",
  "Industrials", "Infrastructures", "Properties & Real Estate", "Technology", "Transportation & Logistic"];
names.forEach((n, i) => {
  const cx = 66 + (i % 3) * 114, cy = 70 + Math.floor(i / 3) * 104;
  drawSectorIcon(svg, n, { cx, cy, S: 0.62 });
  type(svg, cx, cy + 44, n, "label", { fill: TONE.muted, size: 7, anchor: "middle" });
});
