// Crossing 5%, variant C: the top-broker editorial list, for owners. "Who owns DOOH now": each major holder as a
// row with a huge outlined rank, the name, the stake large and a bar true to scale; the newcomer's row is
// highlighted with a NEW chip and its old stake shown as a ghost.
const D = DATA, S = D.s, O = D.owners;
setAccent("buy");
const INK = "#b2d2b9", FILL = "#81a789";

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 48, "Who owns", "hero", { size: 36, weight: 500 });
logoChip(svg, M + 20, y0 + 74, 18, S.logo, S.sym);
type(svg, M + 46, y0 + 86, `${S.sym} now`, "hero", { size: 36, weight: 500, fill: INK });

const rows = O.concat([{ name: "Everyone else", pct: Math.max(0, 100 - O.reduce((s, o) => s + o.pct, 0)), rest: true }]);
// the newcomer's row is taller: it carries its own before → now scale
const TOP = y0 + 118, EXTRA = 62, RH = Math.min(70, (SAFE.bottom - 34 - TOP - EXTRA) / rows.length), max = Math.max(...rows.map((r) => r.pct));
let yAcc = TOP;
rows.forEach((r, i) => {
  const rh = r.mover ? RH + EXTRA : RH, y = yAcc, cy = y + RH / 2;
  yAcc += rh;
  if (r.mover) {
    mk("rect", { x: M - 8, y: y + 4, width: W - 2 * M + 16, height: rh - 8, rx: 12, style: `fill:${FILL};fill-opacity:.1;stroke:${FILL};stroke-opacity:.6;stroke-width:1px` }, svg);
    // own scale, 0–15%: before in grey, the added part in green, the 5% line
    const sx0 = M + 52, sx1 = W - M, sy = y + RH + 14, xs = scale(0, 15, sx0, sx1), h = 10;
    mk("rect", { x: sx0, y: sy, width: sx1 - sx0, height: h, rx: h / 2, style: `fill:${TONE.ground};fill-opacity:.6;stroke:none` }, svg);
    mk("rect", { x: sx0, y: sy, width: xs(S.before) - sx0, height: h, rx: h / 2, style: `fill:${TONE.hi};fill-opacity:.4;stroke:none` }, svg);
    mk("rect", { x: xs(S.before) + 1.5, y: sy, width: xs(S.now) - xs(S.before) - 1.5, height: h, rx: 3, style: `fill:${FILL};stroke:none` }, svg);
    mk("line", { x1: xs(5), y1: sy - 5, x2: xs(5), y2: sy + h + 5, style: `stroke:${TONE.hi};stroke-width:1.2px` }, svg);
    type(svg, xs(S.before) / 2 + sx0 / 2, sy + h + 13, `${S.before.toFixed(2)}% before`, "label", { fill: TONE.muted, size: 6.8, anchor: "middle" });
    type(svg, xs(5), sy - 8, "5% line", "label", { fill: TONE.hi, size: 6.8, weight: 650, anchor: "middle" });
    type(svg, (xs(S.before) + xs(S.now)) / 2, sy + h + 13, `+${(S.now - S.before).toFixed(2)} pts added`, "label", { fill: INK, size: 6.8, weight: 650, anchor: "middle" });
    type(svg, sx1, sy + h + 13, "15%", "label", { fill: TONE.faint, size: 6.4, anchor: "end" });
  }
  if (!r.rest) {
    const n = type(svg, M - 2, cy + 22, String(i + 1), "hero", { size: 62, weight: 700 });
    n.style.fill = "none"; n.style.stroke = r.mover ? INK : TONE.mid; n.style.strokeWidth = "1px";
  }
  const nx = M + 52;
  const nm = r.name.replace(/^PT\s+/, "");
  type(svg, nx, cy - 8, nm, "label", { fill: r.rest ? TONE.muted : TONE.hi, size: 11.5, weight: r.rest ? 500 : 650 });
  if (r.mover) {
    // the change: NEW, how far up the ranking they climbed, and the points added
    const oldRank = O.filter((o) => !o.mover && o.pct > S.before).length + 1, tw = 30;
    mk("rect", { x: nx, y: cy - 2, width: tw, height: 12, rx: 6, style: `fill:${FILL};stroke:none` }, svg);
    type(svg, nx + tw / 2, cy + 6.5, "NEW", "caps", { fill: TONE.ground, size: 5.6, weight: 800, anchor: "middle" });
    const up = `▲ #${oldRank} → #${i + 1}`;
    type(svg, nx + tw + 7, cy + 7, up, "label", { fill: INK, size: 8, weight: 700 });
  }
  type(svg, W - M, cy - 4, `${r.pct.toFixed(2)}%`, "num", { size: r.mover ? 24 : 20, weight: 450, fill: r.mover ? INK : r.rest ? TONE.muted : TONE.hi, anchor: "end" });
  if (!r.mover) {
    const span = W - M - nx, bw = span * (r.pct / max), by = cy + 16;
    mk("rect", { x: nx, y: by, width: span, height: 4, rx: 2, style: `fill:${TONE.card};stroke:none` }, svg);
    mk("rect", { x: nx, y: by, width: bw, height: 4, rx: 2, style: `fill:${TONE.hi};fill-opacity:${r.rest ? 0.2 : 0.45};stroke:none` }, svg);
  }
});

const F = S.facts.map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
