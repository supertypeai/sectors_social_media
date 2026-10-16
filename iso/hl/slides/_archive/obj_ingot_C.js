// Basic Materials · an ingot pallet, style C (technical). The object follows OBJECTS.md §1; the hook reuses
// byan_variants VARIANTS[10]'s layout, plus registration corners round the stage and one dimension line
// (kept height solid, sold height dashed in the accent) — the only extra.
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * A wooden pallet (three runners, one deck) carrying four layers of seven tapered ingots (28 units).
 * keep splits the stack top-to-bottom: the bottom share stays solid, the rest is a dashed accent ghost.
 * lift "solid" draws the moved share in solid accent (a buy).
 */
function drawIngotPallet_C(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" }) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1, b = 0.5) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };

  // 1 · floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2 · runners under the deck
  for (const y of [-22, 0, 22]) block(-46, y - 3, 46, y + 3, 0, 5, "sil", 0.6, 0.3);
  // 3 · the deck
  const Z0 = 5, Z1 = 9;
  block(-46, -25, 46, 25, Z0, Z1, "sil", 1, 0.5);
  // 4 · deck board seams on the two visible faces
  for (let x = -34; x <= 34; x += 11.5) line([x, 25.05, Z0 + 0.6], [x, 25.05, Z1 - 0.6]);
  for (const y of [-12.5, 0, 12.5]) line([46.05, y, Z0 + 0.6], [46.05, y, Z1 - 0.6]);

  // 5 · ingots: long along y, tapered (foot wider than top), layer by layer, far to near
  const N = 7, PITCH = 12.4, LAYERS = 4, TH = 8.6, ingots = [];
  for (let L = 0; L < LAYERS; L++) for (let i = 0; i < N; i++) {
    const x = (i - (N - 1) / 2) * PITCH, z = Z1 + L * TH;
    ingots.push({ x, z, L });
  }
  const shape = (u) => {
    const foot = rrect(u.x - 5.6, -21, u.x + 5.6, 21, 1.2, 4), top = rrect(u.x - 4.2, -19.6, u.x + 4.2, 19.6, 1, 4);
    return { foot, top, z0: u.z, z1: u.z + TH - 0.6 };
  };
  const nKeep = keep == null ? ingots.length : Math.max(1, Math.round(ingots.length * keep));
  ingots.forEach((u, k) => { u.gone = k >= nKeep; }); // already ordered bottom layer first, then x
  const solidIngot = (u, cls) => {
    const s = shape(u);
    mk("path", { d: poly(hull(ringAt(P, s.foot, s.z0).concat(ringAt(P, s.top, s.z1)))), class: cls }, g);
    mk("path", { d: poly(ringAt(P, s.top, s.z1)), class: "nf lo" }, g); // the top face's crease
  };
  const kept = ingots.filter((u) => !u.gone), gone = ingots.filter((u) => u.gone);
  for (const u of kept) solidIngot(u, keep == null ? "sil" : "hi");
  if (lift === "solid") for (const u of gone) solidIngot(u, "acc");
  // 6 · the ghost, last
  else for (const u of gone) {
    const s = shape(u);
    mk("path", { d: poly(hull(ringAt(P, s.foot, s.z0).concat(ringAt(P, s.top, s.z1)))), style: `fill:${TONE.ground};stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;stroke-opacity:.75` }, g);
  }

  const zFull = Z1 + LAYERS * TH - 0.6, zKept = kept.length ? Math.max(...kept.map((u) => u.z + TH - 0.6)) : Z1;
  g.K = K;
  g.anchor = { load: [0, 0, zFull], base: [46, 25, Z0] };
  g.keptAt = kept.length ? [kept[0].x - 5, 21, kept[0].z + TH / 2] : [-46, 25, Z1];
  g.dim = { z0: Z1, zKept, zFull, gone: gone.length > 0 };
  return g;
}

// ---------------------------------------------------------------- the hook (VARIANTS[10] layout)
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });

// registration corners round the stage
const A = { x0: 24, y0: 170, x1: 336, y1: 360 };
for (const [x, yy, dx, dy] of [[A.x0, A.y0, 1, 1], [A.x1, A.y0, -1, 1], [A.x0, A.y1, 1, -1], [A.x1, A.y1, -1, -1]]) {
  mk("path", { d: `M${x} ${yy + dy * 8}V${yy}H${x + dx * 8}`, class: "nf", style: `stroke:${TONE.edge};stroke-width:1px` }, svg);
}

const keep = S.keepOverride ?? S.after / S.before;
const obj = drawIngotPallet_C(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: D.direction === "buy" ? "solid" : "ghost" });
const P = obj.K.P;

// the dimension line: vertical, off the left near corner; kept height solid, gone height dashed accent
{
  const dg = mk("g", {}, svg), X = 56, Y = -30, { z0, zKept, zFull, gone } = obj.dim;
  const at = (z) => P(X, Y, z);
  const seg = (a, b, style) => mk("path", { d: `M${a[0]} ${a[1]}L${b[0]} ${b[1]}`, class: "nf", style }, dg);
  const thin = `stroke:${TONE.edge};stroke-width:1px`;
  for (const z of gone ? [z0, zKept, zFull] : [z0, zFull]) { // extension lines from the stack's corner, and ticks
    seg(P(46, -22, z), P(X + 2, Y, z), `stroke:${TONE.lo};stroke-width:1px`);
    const p = at(z); seg([p[0] - 3, p[1] - 1.5], [p[0] + 3, p[1] + 1.5], thin);
  }
  seg(at(z0), at(zKept), `stroke:${TONE.hi};stroke-width:1px`);
  if (gone) seg(at(zKept), at(zFull), "stroke:var(--acc);stroke-width:1px;stroke-dasharray:2 2.5");
}

leader(svg, P(...obj.anchor.load), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...obj.keptAt), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });

const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
