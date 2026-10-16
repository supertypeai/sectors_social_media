// Crossing 5%, owners podium (top-broker language): the company's major holders as iso columns, heights true to
// stake, the newcomer's column split into what it had (grey) and what it just added (green), with the logo coin
// and a NEW tag on it. A 5% glass line runs across. "Who owns DOOH now" — and who just joined.
const D = DATA, S = D.s, O = D.owners;
setAccent("buy");
const G = "#81a789", GI = "#b2d2b9";
dotField(0, 0, W, H, { fx: W / 2, fy: 440, reach: 300, op: 0.3 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "NEW MAJOR SHAREHOLDER", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, S.day.toUpperCase(), "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 44, "Who owns", "hero", { size: 34, weight: 500 });
logoChip(svg, M + 18, y0 + 70, 16, S.logo, S.sym);
type(svg, M + 42, y0 + 82, `${S.sym} now`, "hero", { size: 34, weight: 500, fill: GI });

const rows = O.slice(0, 4), n = rows.length, fw = 58, gap = 30, dx = 16, dy = 9;
const totalW = n * fw + (n - 1) * gap + dx, x0 = (W - totalW) / 2, base = SAFE.bottom - 66;
// heights: square-root scale so a 5% holder is still visible next to a 51% one; labels carry the exact %
const vmax = Math.max(...rows.map((r) => r.pct)), Hmax = base - (y0 + 168), hv = (v) => Hmax * Math.sqrt(v / vmax);
rows.forEach((r, i) => {
  const x = x0 + i * (fw + gap), h = hv(r.pct), top = base - h, mv = r.mover;
  const seg = (y1, y2, front, side) => {
    if (y2 <= y1) return;
    mk("path", { d: `M${x + fw} ${y1}L${x + fw + dx} ${y1 - dy}L${x + fw + dx} ${y2 - dy}L${x + fw} ${y2}Z`, style: `fill:${side};stroke:none` }, svg);
    mk("rect", { x, y: y1, width: fw, height: y2 - y1, style: `fill:${front};stroke:none` }, svg);
  };
  if (mv) {
    glow(x + fw / 2, top + h / 2, 70, h * 0.6 + 30, 0.1);
    const hb = hv(S.before), mid = base - hb;
    seg(mid, base, "#6c746e", "#4b524d");
    seg(top, mid, G, "#5f7d66");
    mk("line", { x1: x, y1: mid, x2: x + fw, y2: mid, style: `stroke:${TONE.ground};stroke-width:1.2px` }, svg);
    type(svg, x + fw / 2, mid + 14, `${S.before.toFixed(1)}%`, "label", { fill: TONE.hi, size: 7, weight: 650, anchor: "middle" });
    type(svg, x + fw / 2, mid + 23, "before", "label", { fill: TONE.hi, size: 6, anchor: "middle" });
    type(svg, x + fw / 2, top + 16, `+${(S.now - S.before).toFixed(1)}`, "label", { fill: TONE.ground, size: 9, weight: 800, anchor: "middle" });
  } else {
    // the others fade back: dark, low-contrast ghosts with a faint outline
    seg(top, base, "#262320", "#1f1d1a");
    mk("path", { d: `M${x} ${base}V${top}L${x + dx} ${top - dy}H${x + fw + dx}V${base - dy}L${x + fw} ${base}Z`, class: "nf", style: `stroke:${TONE.mid};stroke-width:.7px` }, svg);
  }
  mk("path", { d: `M${x} ${top}L${x + dx} ${top - dy}L${x + fw + dx} ${top - dy}L${x + fw} ${top}Z`, style: `fill:${mv ? "#c5dccb" : "#2e2b27"};stroke:none` }, svg);
  // stake label above
  type(svg, x + fw / 2 + dx / 2, top - dy - (mv ? 54 : 8), `${r.pct.toFixed(r.pct >= 10 ? 1 : 2)}%`, "num", { size: mv ? 24 : 12, weight: mv ? 650 : 450, fill: mv ? GI : TONE.faint, anchor: "middle" });
  if (mv) {
    const ccx = x + fw / 2 + dx / 2, ccy = top - dy / 2 - 20, cr = 15;
    mk("circle", { cx: ccx, cy: ccy + 4, r: cr, style: "fill:#5f7d66" }, svg);
    mk("circle", { cx: ccx, cy: ccy, r: cr + 1.5, style: `fill:${GI}` }, svg);
    logoChip(svg, ccx, ccy, cr - 1, S.logo, S.sym);
    mk("rect", { x: ccx - 14, y: top - dy - 50, width: 28, height: 11, rx: 5.5, style: `fill:${G}` }, svg);
    type(svg, ccx, top - dy - 42, "NEW", "caps", { fill: TONE.ground, size: 5.4, weight: 800, anchor: "middle" });
  }
  // name under the floor, two lines max, no ellipsis
  const nm = r.name.replace(/^PT\s+/, "");
  wrapText(nm, 7, fw + 10, 0.55).slice(0, 2).forEach((l, k) => type(svg, x + fw / 2, base + 14 + k * 9, l, "label", { fill: mv ? GI : TONE.faint, size: mv ? 8 : 6.6, weight: mv ? 750 : 450, anchor: "middle" }));
});
mk("line", { x1: M - 6, y1: base, x2: W - M, y2: base, style: `stroke:${TONE.mid};stroke-width:1px` }, svg);
// 5% line across
const p5 = base - hv(5);
// the 5% level as a thin iso plane: a front edge, a back edge set back by the columns' depth, and hatching
// between them, so it reads as a floor the columns pass through
{
  // the plane is hidden wherever a column stands in it (a mask cut by each column's silhouette above the plane's
  // back edge), and each column gets its own cut line, so the plane reads as passing through, not in front
  const cols = rows.map((r, i) => ({ x: x0 + i * (fw + gap), top: base - hv(r.pct), mv: r.mover }));
  const px0 = M - 6, x1 = W - M - dx, bx = dx, by = -dy;
  const mask = mk("mask", { id: "plane5", maskUnits: "userSpaceOnUse", x: 0, y: 0, width: W, height: H }, mk("defs", {}, svg));
  mk("rect", { x: 0, y: 0, width: W, height: H, fill: "#fff" }, mask);
  for (const c of cols) {
    // a column that stops at or just above the line (within the plane's thickness) sits ON the plane: the plane
    // stays fully drawn over it, like a lid
    if (c.top > p5 - dy * 2) continue;
    // a column that pierces the plane: cut out its own cross-section plus the band of its front face (plane
    // behind that face is hidden by it); the plane beside it, in front of its side face, stays visible
    mk("path", { d: `M${c.x} ${p5}H${c.x + fw}L${c.x + fw + dx} ${p5 - dy}H${c.x}Z`, fill: "#000" }, mask);
  }
  const pg = mk("g", { opacity: 0.95, mask: "url(#plane5)" }, svg);
  mk("path", { d: `M${px0} ${p5}L${x1} ${p5}L${x1 + bx} ${p5 + by}L${px0 + bx} ${p5 + by}Z`, style: `fill:${GI};fill-opacity:.1;stroke:none` }, pg);
  for (let x = px0 + 5; x < x1; x += 5) mk("line", { x1: x, y1: p5, x2: x + bx, y2: p5 + by, style: `stroke:${GI};stroke-width:.7px;opacity:.7` }, pg);
  mk("line", { x1: px0 + bx, y1: p5 + by, x2: x1 + bx, y2: p5 + by, style: `stroke:${GI};stroke-width:.9px;stroke-dasharray:4 3` }, pg);
  // the front edge runs in front of every column, unmasked
  mk("line", { x1: px0, y1: p5, x2: x1, y2: p5, style: `stroke:${GI};stroke-width:1.1px;stroke-dasharray:4 3;opacity:.95` }, svg);
  mk("line", { x1: x1, y1: p5, x2: x1 + bx, y2: p5 + by, style: `stroke:${GI};stroke-width:.9px` }, pg);
  // where the plane cuts each column: a line across its front face and up its side face
  for (const c of cols) {
    if (c.top > p5 - dy * 2) continue;
    mk("path", { d: `M${c.x + fw} ${p5}L${c.x + fw + dx} ${p5 - dy}`, class: "nf",
      style: `stroke:${c.mv ? TONE.ground : GI};stroke-width:1.2px;stroke-dasharray:4 3;opacity:${c.mv ? 0.55 : 0.6}` }, svg);
  }
}
type(svg, M - 4, p5 + 12, "5% line", "label", { fill: GI, size: 7, weight: 700 });

const F = S.facts.map((f) => `${f.value} ${f.label}`).join("  ·  ");
type(svg, M, SAFE.bottom - 4, F, "label", { fill: TONE.hi, size: 8, weight: 600 });
type(svg, W - M, SAFE.bottom - 4, "sectors.app", "label", { fill: TONE.muted, size: 7.4, anchor: "end", weight: 650 });
grain(0.09);
