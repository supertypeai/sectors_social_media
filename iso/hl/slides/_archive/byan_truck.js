// Hook object for BYAN (a coal miner): one detailed mining haul truck, loaded with coal. It does not act
// out the story; it is the thing that says "coal" before a word is read. The coal is the only accent.
// Text on top as in stake_split: hero number, one sentence, one quiet line. Same DATA.slide.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

typeRun(svg, M - 3, 118, [[S.hero.num, 82, 220], [S.hero.unit, 34, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 148, sentence, "title", { accent: [] });
type(svg, M, y + 17, S.deal ? `${S.seller} → ${S.holder}` : `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}% · ${S.day}`, "body", { fill: TONE.muted });

// ---------------------------------------------------------------- the truck (world units, z up, front at +x)
// zoomed in: the camera frames the rear tyre and the loaded body's back corner, and the truck runs off the
// right edge; a clip keeps it inside the slide, clear of the footer
const K = camera(3.1, [[-62, 12, 0], [-8, 27, 0], [-60, 0, 62], [-8, 26, 50]], 196, 318);
const clip = mk("clipPath", { id: "stage" }, mk("defs", {}, svg));
mk("rect", { x: 0, y: 196, width: W, height: H - 196 - 34 }, clip);
const g = mk("g", { "clip-path": "url(#stage)" }, svg);
const P = K.P;
const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1.6, b = 1) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); return slab(g, K, ring, inner, z0, z1, cls); };
const facePoly = (pts, cls = "nf lo") => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls }, g);

/** A tyre: a cylinder lying along y, from y0 (far) to y1 (near), with tread across its band and a hub. */
function tyre(cx, y0, y1, R) {
  const N = 40, A = [], B = [];
  for (let k = 0; k < N; k++) {
    const a = (k / N) * Math.PI * 2, x = cx + Math.cos(a) * R, z = R + Math.sin(a) * R;
    A.push([x, y0, z]); B.push([x, y1, z]);
  }
  mk("path", { d: poly(hull(A.concat(B).map((p) => P(...p)))), class: "sil" }, g);
  // tread across the band, only where the band faces the camera (else it shows through the silhouette)
  for (let k = 0; k < N; k += 2) {
    const a = (k / N) * Math.PI * 2;
    if (Math.cos(a) * 0.61 + Math.sin(a) * 0.5 > 0.05) line(A[k], B[k]);
  }
  mk("path", { d: poly(B.map((p) => P(...p))), class: "sil" }, g);       // the near sidewall covers the back
  const ring = (r, dy = 0.15) => mk("path", { d: poly(B.map(([x, , z]) => P(cx + (x - cx) * r, y1 + dy, R + (z - R) * r))), class: "nf lo" }, g);
  ring(0.72); ring(0.5); ring(0.22);
  for (let k = 0; k < 8; k++) {                                           // wheel nuts
    const a = (k / 8) * Math.PI * 2, [sx, sy] = P(cx + Math.cos(a) * R * 0.36, y1 + 0.2, R + Math.sin(a) * R * 0.36);
    mk("circle", { cx: sx, cy: sy, r: 0.55, fill: TONE.edge }, g);
  }
}

mirror(g, K, rings(-60, -26, 62, 26, 4, 1)[0], 0, 14);
floor(g, K, -90, -60, 100, 60, 10);

// far side wheels first
tyre(-34, -27, -19, 15); tyre(-34, -18, -12, 15); tyre(40, -26, -17, 15);
// chassis rails and axles
block(-52, -12, 50, -6, 13, 19); block(-52, 6, 50, 12, 13, 19);
block(-36, -18, -32, 18, 13, 16, "nf lo"); block(38, -18, 42, 18, 13, 16, "nf lo");

// dump body: tall, ribbed on its near side and tail, sloping floor shown by one crease
block(-60, -26, 24, 26, 19, 50, "sil", 3, 1.6);
for (const x of [-50, -38, -26, -14, -2, 10]) line([x, 26.05, 21], [x, 26.05, 49]);   // side ribs
line([-58, 26.05, 30], [22, 26.05, 30]);                                               // a rub rail
for (const yy of [-16, -6, 4, 14]) line([24.05, yy, 22], [24.05, yy, 48]);              // front wall ribs (visible +x)
// the canopy over the cab, cantilevered from the body
block(24, -26, 62, 26, 47, 50, "sil", 2, 1);
for (const x of [32, 42, 52]) line([x, 26.05, 47.5], [x, 26.05, 49.5]);

// the load: coal lumps heaped in the body, higher in the middle. Each lump owns one grid cell and is smaller
// than it, so no two lumps intersect; painted far to near (x + y), a lump is always drawn after anything
// behind it. A smooth heap underneath fills the gaps.
const CELL = 10.5, lumps = [];
for (let x = -55; x <= 18; x += CELL) for (let yy = -21; yy <= 21; yy += CELL) {
  const n = Math.sin(x * 12.9898 + yy * 78.233) * 43758.5453, j = n - Math.floor(n); // stable jitter in [0,1)
  const h = 1 - ((x + 18) / 42) ** 2 - (yy / 26) ** 2;
  if (h < 0.05) continue;
  const s = CELL * (0.32 + 0.12 * j); // half-size, < CELL / 2
  lumps.push({ x: x + (j - 0.5) * 1.5, y: yy, z: 50 + h * 10, s, th: 3 + j * 2.5 });
}
for (const [R, z0, z1, ox] of [[30, 48, 51.5, -18], [22, 51.5, 54.5, -18], [13, 54.5, 57, -18]]) { // the heap
  const [hr, hi] = rings(-18 - R * 1.3, -R * 0.8, -18 + R * 1.3, R * 0.8, R * 0.7, 1);
  slab(g, K, hr, hi, z0, z1, "nf lo");
}
lumps.sort((a, b) => a.x + a.y - (b.x + b.y) || a.z - b.z);
for (const l of lumps) block(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, l.z - l.th, l.z, "acc", 1.8, 0.7);

// front deck with handrails, the cab on its far-left, the engine bay and grille below
block(26, -26, 62, 26, 27, 29, "sil", 1.5, 0.8);
block(40, -24, 58, -6, 29, 45, "sil", 2, 1);                             // cab
facePoly([[58.05, -22, 43], [58.05, -8, 43], [58.05, -8, 35], [58.05, -22, 35]]);        // windscreen
facePoly([[42, -5.95, 43], [56, -5.95, 43], [56, -5.95, 35], [42, -5.95, 35]]);          // side window
block(46, -2, 52, 4, 29, 46, "sil", 1.2, 0.5); block(46, 8, 52, 14, 29, 44, "sil", 1.2, 0.5); // exhaust stacks + air intake
block(44, -18, 62, 20, 17, 27, "sil", 2, 1);                             // engine bay / radiator housing
for (let k = 0; k < 9; k++) line([62.05, -14 + k * 3.6, 18.5], [62.05, -14 + k * 3.6, 25.5]); // grille slats
for (const yy of [-15, 17]) { const [sx, sy] = P(62.1, yy, 22); mk("circle", { cx: sx, cy: sy, r: 1.6, class: "nf", style: `stroke:${TONE.hi}` }, g); } // headlights, on the radiator face
// handrail round the deck: a few posts and one rail along the near and front edges
for (const [x, yy] of [[30, 25], [45, 25], [61, 25], [61, 5], [61, -15]]) line([x, yy, 29], [x, yy, 36], "nf lo");
line([30, 25, 36], [61, 25, 36], "nf lo"); line([61, 25, 36], [61, -15, 36], "nf lo");
// the access ladder, diagonal down the front-right
for (let k = 0; k <= 6; k++) { const t = k / 6; line([62 + t * 6, 18, 27 - t * 22], [62 + t * 6, 24, 27 - t * 22]); }
line([62, 18, 27], [68, 18, 5], "nf"); line([62, 24, 27], [68, 24, 5], "nf");
// mirrors on arms
line([58, -24, 40], [64, -28, 41], "nf"); block(63, -30, 65, -27, 37, 42, "sil", 0.6, 0.3);

// near side wheels last
tyre(-34, 12, 18, 15); tyre(-34, 19, 27, 15); tyre(40, 17, 26, 15);
