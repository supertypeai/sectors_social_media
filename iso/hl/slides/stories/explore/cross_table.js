// Crossing 5%, Premier-League-table style: a big stacked title, then one row per new major shareholder with
// BEFORE | NOW | CHANGE columns. The biggest change is the highlighted top row.
const D = DATA, R = D.rows.slice(0, 8);
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";
glow(W * 0.85, SAFE.top + 60, 160, 110, 0.18);

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "OWNERSHIP", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company.toUpperCase(), "caps", { fill: TONE.muted, weight: 700, anchor: "end" });

type(svg, W - M, y0 + 46, "NEW", "hero", { size: 40, weight: 400, anchor: "end" });
type(svg, W - M, y0 + 86, "MAJOR", "hero", { size: 40, weight: 800, fill: INK, anchor: "end" });
type(svg, W - M, y0 + 122, "SHAREHOLDERS", "hero", { size: 30, weight: 400, anchor: "end" });

// columns
const cB = W - M - 96, cN = W - M - 52, cC = W - M - 4, HY = y0 + 156;
type(svg, cB, HY, "BEFORE", "caps", { fill: TONE.muted, size: 5.6, anchor: "end" });
type(svg, cN, HY, "NOW", "caps", { fill: TONE.muted, size: 5.6, anchor: "end" });
type(svg, cC, HY, "CHANGE", "caps", { fill: TONE.muted, size: 5.6, anchor: "end" });

const TOP = HY + 8, RH = Math.min(46, (SAFE.bottom - 30 - TOP) / R.length);
R.forEach((r, i) => {
  const y = TOP + i * RH + 3, h = RH - 6, cy = y + h / 2, first = i === 0;
  mk("rect", { x: M - 6, y, width: W - 2 * M + 12, height: h, rx: 6,
    style: first ? `fill:${FILL};stroke:none` : `fill:${TONE.card};fill-opacity:.8;stroke:${TONE.lo};stroke-width:.8px` }, svg);
  const fg = first ? TONE.ground : TONE.hi, sub = first ? "#2a3a2d" : TONE.muted;
  logoChip(svg, M + 9, cy, 10, r.logo, r.sym);
  type(svg, M + 25, cy - 1.5, r.sym, "label", { fill: fg, size: 10, weight: 800 });
  const nm = r.holder.length > 24 ? r.holder.split(" ").slice(0, 3).join(" ") : r.holder;
  type(svg, M + 25, cy + 9, nm, "label", { fill: sub, size: 7, weight: 600 });
  type(svg, cB, cy + 4, r.before.toFixed(2), "label", { fill: sub, size: 10, weight: 500, anchor: "end" });
  type(svg, cN, cy + 4, r.now.toFixed(2), "label", { fill: fg, size: 10, weight: 700, anchor: "end" });
  type(svg, cC, cy + 4.5, `+${(r.now - r.before).toFixed(2)}`, "label", { fill: first ? TONE.ground : INK, size: 11, weight: 800, anchor: "end" });
});

type(svg, M, SAFE.bottom - 4, "% of the company · owning 5% or more = major shareholder", "label", { fill: TONE.hi, size: 8.2, weight: 600 });
grain(0.09);
