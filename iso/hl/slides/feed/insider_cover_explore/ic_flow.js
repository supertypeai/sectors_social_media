// Insider cover, approach 3 — a proportional flow: the stake drawn as a ribbon from where it was to where it
// went (seller to buyer, or holder to the market). Heights are to scale (1% of the company = the same height).
// DATA.slide: the vp_cover payload from image_generator/insider_v_people.build().
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);
grain(0.05);

const pc = (v) => (v < 0.005 ? "0%" : (v >= 10 ? v.toFixed(1) : v.toFixed(2)).replace(/\.?0+$/, "") + "%");
const moved = Math.abs(S.after - S.before);
const short = (n) => n.split(" ").slice(0, 2).join(" ");

// ---------------------------------------------------------------- the line on top
const hl = `${S.holder.name} ${S.headline}`;
let y = 66;
const hs = 19, lines = wrapText(hl, hs, W - 2 * M, 0.48);
for (const l of lines.slice(0, 3)) {
  const t = type(svg, M, y, "", "title", { size: hs, weight: 520 });
  t.innerHTML = l.split(" ").map((w) => S.accent.includes(w) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
  y += hs * 1.12;
}

// ---------------------------------------------------------------- the flow
// left: where the shares were. right: [kept by the source, moved to the destination]
const src = S.other ? { name: short(S.other.name), was: S.otherBefore, kept: S.otherAfter }
  : S.sell ? { name: short(S.holder.name), was: S.before, kept: S.after }
  : { name: "Other holders", was: moved, kept: 0, market: true };
const dst = S.sell && !S.other ? { name: "The market", sub: "public float", market: true }
  : { name: short(S.holder.name), sub: S.before > 0.005 ? `was ${pc(S.before)}` : "new holder", pre: S.before };
const top = y + 18, avail = 392 - 40 - top;
const k = Math.min(5.2, avail / Math.max(src.was, moved + (dst.pre || 0)));
const nx0 = M + 70, nw = 10, nx1 = W - M - 92;
const keptH = src.kept * k, movH = moved * k;
const g = mk("g", {}, svg);
// source node
mk("rect", { x: nx0, y: top, width: nw, height: src.was * k, rx: 1.5, style: `fill:${src.market ? TONE.mid : TONE.edge};stroke:none` }, g);
// the kept part flows straight on, grey; the moved part arcs down/over in the accent
const gap = keptH > 0.5 ? 14 : 0;
const ribbon = (ya, yb, h, fill, op) => {
  const xa = nx0 + nw, xb = nx1, cx = (xa + xb) / 2;
  mk("path", { d: `M${xa},${ya} C${cx},${ya} ${cx},${yb} ${xb},${yb} L${xb},${yb + h} C${cx},${yb + h} ${cx},${ya + h} ${xa},${ya + h} Z`,
    style: `fill:${fill};fill-opacity:${op};stroke:none` }, g);
};
const dy0 = top + keptH + gap; // destination node top
if (keptH > 0.5) {
  ribbon(top, top, keptH, TONE.edge, 0.22);
  mk("rect", { x: nx1, y: top, width: nw, height: keptH, rx: 1.5, style: `fill:${TONE.edge};stroke:none` }, g);
}
const preH = (dst.pre || 0) * k;
ribbon(top + keptH, dy0 + preH, movH, "var(--acc)", 0.55);
if (preH > 0.5) mk("rect", { x: nx1, y: dy0, width: nw, height: preH, rx: 1.5, style: "fill:var(--acc);fill-opacity:.45;stroke:none" }, g);
if (dst.market) mk("rect", { x: nx1, y: dy0, width: nw, height: movH, rx: 1.5, style: "fill:none;stroke:var(--acc);stroke-width:1px;stroke-dasharray:2 1.6" }, g);
else mk("rect", { x: nx1, y: dy0 + preH, width: nw, height: movH, rx: 1.5, style: "fill:var(--acc);stroke:none" }, g);

// the moved amount, set on the ribbon
const my = (top + keptH + dy0 + preH) / 2 + movH / 2;
typeRun(svg, (nx0 + nx1) / 2 + nw / 2, my + 8, [[pc(moved).slice(0, -1), 26, 400, TONE.hi], ["%", 13, 400, TONE.hi]], { anchor: "middle" });

// node labels
const label = (x, yy, anchor, a, b, c) => {
  type(svg, x, yy, a, "label", { size: 9.6, weight: 650, anchor });
  if (b) type(svg, x, yy + 12, b, "label", { size: 8.6, fill: TONE.muted, anchor });
  if (c) type(svg, x, yy + 23, c, "label", { size: 7.4, fill: TONE.faint, anchor });
};
label(nx0 - 7, top + 8, "end", src.name, src.market ? "" : `held ${pc(src.was)}`, S.other ? "the seller" : src.market ? "" : S.sell ? "the seller" : "");
if (keptH > 0.5) label(nx1 + nw + 7, top + 8, "start", src.name, `keeps ${pc(src.kept)}`);
else if (!src.market) { /* nothing kept: say so under the source */ type(svg, nx0 - 7, top + src.was * k + 12, "keeps 0%", "label", { size: 7.2, fill: "var(--acc)", anchor: "end" }); }
label(nx1 + nw + 7, dy0 + 8, "start", dst.name, dst.market ? dst.sub : `now ${pc(S.after)}`, dst.market ? "" : dst.sub);

// scale key
const ky = 362;
mk("rect", { x: M, y: ky - 10 * k + 2, width: 4, height: 10 * k, style: `fill:${TONE.mid};stroke:none` }, svg);
type(svg, M + 8, ky, `= 10% of ${S.sym}`, "label", { size: 6.6, fill: TONE.faint });

// byline
const ly = 398;
mk("line", { x1: M, y1: ly - 16, x2: W - M, y2: ly - 16, class: "lo thin" }, svg);
typeRun(svg, M, ly, [[S.value, 13, 450, "var(--acc)"], ["  deal value", 7.5, 500, TONE.muted]]);
type(svg, W - M, ly, `${S.span} ${S.year}`, "label", { size: 7.5, fill: TONE.muted, anchor: "end" });
