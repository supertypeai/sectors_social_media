// Hook object for BYAN: its flame mark, built as a solid (Hairline's "figure drawn from a mark").
// The logo's colour layers become depth: nested flame-shaped plates stand upright and step towards us,
// outer flame at the back, the drop at the front. Outlines only; the drop is the one accent.
// Text on top as in stake_split. Same DATA.slide.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

typeRun(svg, M - 3, 118, [[S.hero.num, 82, 220], [S.hero.unit, 34, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 148, sentence, "title", { accent: [] });
type(svg, M, y + 17, S.deal ? `${S.seller} → ${S.holder}` : `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}% · ${S.day}`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- the mark, traced in (u, v), v up
/** A closed Catmull-Rom curve through control points, sampled `per` points per span. */
function closedCurve(cp, per = 10) {
  const out = [], n = cp.length;
  for (let i = 0; i < n; i++) {
    const p0 = cp[(i - 1 + n) % n], p1 = cp[i], p2 = cp[(i + 1) % n], p3 = cp[(i + 2) % n];
    for (let k = 0; k < per; k++) {
      const t = k / per, t2 = t * t, t3 = t2 * t;
      const f = (a, b, c, d) => 0.5 * (2 * b + (-a + c) * t + (2 * a - 5 * b + 4 * c - d) * t2 + (-a + 3 * b - 3 * c + d) * t3);
      out.push([f(p0[0], p1[0], p2[0], p3[0]), f(p0[1], p1[1], p2[1], p3[1])]);
    }
  }
  return out;
}
// the outer flame: round base, a tall tongue up-right, a notch, a smaller tongue up-left
const FLAME = [[0, 0], [24, 3], [40, 18], [45, 38], [41, 58], [33, 74], [27, 88], [26, 104], [17, 92], [8, 78], [3, 68],
  [-1, 76], [-4, 88], [-12, 78], [-24, 66], [-36, 50], [-43, 32], [-39, 14], [-24, 3]];
const shrink = (pts, k, cu = 0, cv = 30) => pts.map(([u, v]) => [cu + (u - cu) * k, cv + (v - cv) * k]);
// a teardrop, tip up, for the inner layers
const DROP = [[0, 0], [16, 4], [24, 18], [22, 34], [12, 50], [0, 64], [-12, 50], [-22, 34], [-24, 18], [-16, 4]];
const LAYERS = [ // [outline, depth from, depth to, class]
  [closedCurve(FLAME), 0, 10, "sil"],
  [closedCurve(shrink(FLAME, 0.84, 2, 26)), 10, 16, "sil"],
  [closedCurve(DROP.map(([u, v]) => [u * 1.42 + 2, v * 1.12])), 16, 22, "sil"],
  [closedCurve(DROP.map(([u, v]) => [u * 1.05 + 2, v * 0.86 + 6])), 22, 26, "sil"],
  [closedCurve(DROP.map(([u, v]) => [u * 0.7 + 2, v * 0.6 + 12])), 26, 30, "sil"],
  [closedCurve(DROP.map(([u, v]) => [u * 0.36 + 2, v * 0.34 + 20])), 30, 34, "acc"],
];

// ---------------------------------------------------------------- upright extrusion, painted far to near
// A plate stands in the x–z plane (x = u, z = v) and runs in depth along y. We draw only the side faces
// that face the camera, far ones first, then the plate's front face on top; plates go back to front.
const K = camera(1.75, [[-45, 0, 0], [46, 34, 0], [-45, 0, 106], [46, 34, 104]], 180, 300);
const g = mk("g", {}, svg);
const VIEW = [0.61, 0.61, 0.5]; // towards the camera (azimuth 45°, k 0.5)
floor(g, K, -80, -40, 80, 70, 9);
// a shadow-plate on the floor under the mark, so it stands on something
{ const [r, i] = rings(-48, -6, 50, 40, 10, 1.2); slab(g, K, r, i, 0, 2, "nf lo"); }

function plate(outline, y0, y1, cls) {
  const W3 = (u, v, yy) => K.P(u, yy, v + 2);
  const n = outline.length, sides = [];
  // the outline runs counter-clockwise in (u, v); an edge's outward normal is (dv, -du)
  let area = 0;
  for (let i = 0; i < n; i++) { const [a, b] = [outline[i], outline[(i + 1) % n]]; area += a[0] * b[1] - b[0] * a[1]; }
  const sgn = area > 0 ? 1 : -1;
  for (let i = 0; i < n; i++) {
    const a = outline[i], b = outline[(i + 1) % n];
    const nu = sgn * (b[1] - a[1]), nv = sgn * -(b[0] - a[0]);
    if (nu * VIEW[0] + nv * VIEW[2] <= 0) continue; // faces away
    sides.push({ a, b, key: (a[0] + b[0]) * VIEW[0] + (a[1] + b[1]) * VIEW[2] });
  }
  sides.sort((p, q) => p.key - q.key);
  // the side wall as one shape with one outline: stroke every strip thick, then repaint the strips with
  // fill only, which covers the seams between them and the inner half of the stroke, leaving the rim
  const quad = ({ a, b }) => poly([W3(a[0], a[1], y0), W3(b[0], b[1], y0), W3(b[0], b[1], y1), W3(a[0], a[1], y1)]);
  const wall = sides.map(quad).join("");
  mk("path", { d: wall, style: `fill:${TONE.ground};stroke:${TONE.mid};stroke-width:2.6px` }, g);
  mk("path", { d: wall, style: `fill:${TONE.ground};stroke:none` }, g);
  mk("path", { d: poly(outline.map(([u, v]) => W3(u, v, y1))), class: cls }, g); // the front face
}
for (const [outline, y0, y1, cls] of LAYERS) plate(outline, y0, y1, cls);
