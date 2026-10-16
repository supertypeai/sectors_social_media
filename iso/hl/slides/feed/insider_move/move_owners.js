// Post #1, slide 3: who owns the company now, as one donut. The mover's slice is the accent and starts at
// twelve o'clock; a dashed outer arc shows how big it was before. The rest are greys, biggest first, named
// in a short legend underneath.
// DATA.slide: { title, accent[], sym, holder, before, after, rows: [{ name, pct, mover }] }
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let ty = para(svg, M, 74, S.title, "title", { accent: S.accent ?? [] });

// slices: the mover first, then the others biggest first, then whatever is left as "everyone else"
const mover = S.rows.find((r) => r.mover);
const others = S.rows.filter((r) => !r.mover).slice(0, 4);
const named = (mover ? [mover] : []).concat(others);
const rest = Math.max(0, 100 - named.reduce((s, r) => s + r.pct, 0));
const slices = named.concat(rest > 0.05 ? [{ name: "Everyone else", pct: rest, rest: true }] : []);

const CX = W / 2, CY = ty + 118, R = 84, T = 20; // centre, outer radius, ring thickness
const pt = (a, r) => [CX + r * Math.sin(a), CY - r * Math.cos(a)];
const arc = (a0, a1, r0, r1) => {
  const big = a1 - a0 > Math.PI ? 1 : 0, [p, q, s, t] = [pt(a0, r1), pt(a1, r1), pt(a1, r0), pt(a0, r0)];
  return `M${p}A${r1} ${r1} 0 ${big} 1 ${q}L${s}A${r0} ${r0} 0 ${big} 0 ${t}Z`;
};
const GAP = 0.02, greys = [0.2, 0.13, 0.09, 0.06, 0.04];
let a = 0, gi = 0;
const g = mk("g", {}, svg);
for (const sl of slices) {
  const a1 = a + (sl.pct / 100) * Math.PI * 2;
  if (a1 - a > GAP * 2) {
    const style = sl.mover
      ? "fill:var(--acc);fill-opacity:.32;stroke:var(--acc);stroke-width:1.4px"
      : sl.rest ? `fill:${TONE.hi};fill-opacity:.025;stroke:${TONE.mid};stroke-width:1px;stroke-dasharray:1.5 3`
      : `fill:${TONE.hi};fill-opacity:${greys[gi++]};stroke:${TONE.edge};stroke-width:1px`;
    mk("path", { d: arc(a + GAP, a1 - GAP, R - T, R), style }, g);
  }
  sl.mid = (a + a1) / 2;
  a = a1;
}

// the mover's stake before the move: a dashed arc just outside the ring
if (S.before > S.after) { // also when the mover has left the list entirely
  const a1 = (S.before / 100) * Math.PI * 2, r = R + 7;
  const [p, q] = [pt(0.01, r), pt(a1, r)];
  mk("path", { d: `M${p}A${r} ${r} 0 ${a1 > Math.PI ? 1 : 0} 1 ${q}`, class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 3;stroke-width:1.2px;opacity:.85" }, g);
  const [lx, ly] = pt(a1, r + 6);
  type(g, lx + 3, ly + 3, `was ${S.before.toFixed(2)}%`, "label", { fill: "var(--acc)", size: 7.4, weight: 650, anchor: a1 > Math.PI ? "end" : "start" });
}

// the centre: the mover's stake now
{
  typeRun(svg, CX, CY + 6, [[S.after.toFixed(2), 30, 260, "var(--acc)"], ["%", 13, 300, TONE.muted]], { anchor: "middle" });
  type(svg, CX, CY + 20, S.holder.length > 22 ? S.holder.slice(0, 21) + "…" : S.holder, "label", { fill: TONE.hi, size: 7.4, weight: 600, anchor: "middle" });
  type(svg, CX, CY - 22, "NOW", "caps", { fill: TONE.faint, size: 5.6, anchor: "middle" });
}

// ---------------------------------------------------------------- legend
let ly = CY + R + 30;
gi = 0;
for (const sl of slices) {
  const swatch = sl.mover ? "fill:var(--acc);fill-opacity:.5;stroke:var(--acc)"
    : sl.rest ? `fill:none;stroke:${TONE.mid};stroke-dasharray:1.5 2` : `fill:${TONE.hi};fill-opacity:${greys[gi++]};stroke:${TONE.edge}`;
  mk("rect", { x: M, y: ly - 6.5, width: 7, height: 7, rx: 1.5, style: `${swatch};stroke-width:1px` }, svg);
  type(svg, M + 13, ly, sl.name.length > 38 ? sl.name.slice(0, 37) + "…" : sl.name, "label", { fill: sl.mover ? TONE.hi : TONE.muted, size: 8, weight: sl.mover ? 650 : 500 });
  type(svg, W - M, ly, `${sl.pct.toFixed(2)}%`, "label", { fill: sl.mover ? "var(--acc)" : TONE.hi, size: 8, weight: 600, anchor: "end" });
  ly += 13.5;
}
