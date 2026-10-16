// Reusable hairline objects. Each draws into a parent group with its own camera, so a slide can stack
// them (a faint mark behind, a focal object in front). render.mjs pastes this after style.js.

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
const VIEW_DIR = [0.61, 0.61, 0.5]; // towards the camera at azimuth 45°, k 0.5

/**
 * An upright plate: a closed outline in (u, v) standing in the x–z plane, running in depth y0..y1.
 * Draws only the camera-facing side wall (as one shape with one rim) and then the front face.
 */
function uprightPlate(g, K, outline, y0, y1, cls = "sil", lift = 0) {
  const W3 = (u, v, yy) => K.P(u, yy, v + lift);
  const n = outline.length, sides = [];
  let area = 0;
  for (let i = 0; i < n; i++) { const a = outline[i], b = outline[(i + 1) % n]; area += a[0] * b[1] - b[0] * a[1]; }
  const sgn = area > 0 ? 1 : -1;
  for (let i = 0; i < n; i++) {
    const a = outline[i], b = outline[(i + 1) % n];
    const nu = sgn * (b[1] - a[1]), nv = sgn * -(b[0] - a[0]);
    if (nu * VIEW_DIR[0] + nv * VIEW_DIR[2] <= 0) continue;
    sides.push({ a, b, key: (a[0] + b[0]) * VIEW_DIR[0] + (a[1] + b[1]) * VIEW_DIR[2] });
  }
  sides.sort((p, q) => p.key - q.key);
  const wall = sides.map(({ a, b }) => poly([W3(a[0], a[1], y0), W3(b[0], b[1], y0), W3(b[0], b[1], y1), W3(a[0], a[1], y1)])).join("");
  mk("path", { d: wall, style: `fill:${TONE.ground};stroke:${TONE.mid};stroke-width:2.6px` }, g);
  mk("path", { d: wall, style: `fill:${TONE.ground};stroke:none` }, g);
  mk("path", { d: poly(outline.map(([u, v]) => W3(u, v, y1))), class: cls }, g);
}

// ---------------------------------------------------------------- BYAN's flame mark, as a solid
const FLAME_CP = [[0, 0], [24, 3], [40, 18], [45, 38], [41, 58], [33, 74], [27, 88], [26, 104], [17, 92], [8, 78], [3, 68],
  [-1, 76], [-4, 88], [-12, 78], [-24, 66], [-36, 50], [-43, 32], [-39, 14], [-24, 3]];
const DROP_CP = [[0, 0], [16, 4], [24, 18], [22, 34], [12, 50], [0, 64], [-12, 50], [-22, 34], [-24, 18], [-16, 4]];

/** The flame mark: nested upright plates stepping towards us; the drop is `dropCls`. Returns its group. */
function drawFlameMark(parent, { S = 1.75, cx = 180, cy = 300, depth = 1, dropCls = "acc", floorOn = true } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-45, 0, 0], [46, 34 * depth, 0], [-45, 0, 106], [46, 34 * depth, 104]], cx, cy);
  const shrink = (pts, k, cu, cv) => pts.map(([u, v]) => [cu + (u - cu) * k, cv + (v - cv) * k]);
  const layers = [
    [closedCurve(FLAME_CP), 0, 10],
    [closedCurve(shrink(FLAME_CP, 0.84, 2, 26)), 10, 16],
    [closedCurve(DROP_CP.map(([u, v]) => [u * 1.42 + 2, v * 1.12])), 16, 22],
    [closedCurve(DROP_CP.map(([u, v]) => [u * 1.05 + 2, v * 0.86 + 6])), 22, 26],
    [closedCurve(DROP_CP.map(([u, v]) => [u * 0.7 + 2, v * 0.6 + 12])), 26, 30],
    [closedCurve(DROP_CP.map(([u, v]) => [u * 0.36 + 2, v * 0.34 + 20])), 30, 34, dropCls],
  ];
  if (floorOn) {
    floor(g, K, -80, -40, 80, 70, 9);
    const [r, i] = rings(-48, -6, 50, 40 * depth, 10, 1.2);
    slab(g, K, r, i, 0, 2, "nf lo");
  }
  for (const [outline, y0, y1, cls] of layers) uprightPlate(g, K, outline, y0 * depth, y1 * depth, cls ?? "sil", 2);
  return g;
}

// ---------------------------------------------------------------- a coal mine cart on a short rail
/**
 * One simple silhouette (a tapered tub on four wheels) carried by fine detail: a rolled rim, rivet rows,
 * strap bands, axle boxes, sleepers, and a heap of coal lumps (the accent). Painted far to near.
 */
function drawMineCart(parent, { S = 2.3, cx = 180, cy = 330, track = true, keep = null, lift = 30 } = {}) {
  // keep: fraction of the load that stays (null = all coal in the accent, as before). With keep set, the
  // kept lumps (rear of the tub) stay bright, the rest lift `lift` units up in the accent and fade.
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P, front = K.front;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1, b = 0.5) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  const dot = (p, r = 0.7, fill = TONE.edge) => { const [x, y] = P(...p); mk("circle", { cx: x, cy: y, r, fill }, g); };

  if (track) {
    floor(g, K, -80, -50, 80, 50, 8);
    // track: sleepers, then the far rail
    for (let x = -36; x <= 36; x += 12) block(x - 3, -26, x + 3, 26, 0, 1.6, "sil", 0.6, 0.3);
    block(-42, -19, 42, -16, 1.6, 4, "sil", 0.6, 0.3);
  }

  const wheel = (wx, wy, R = 7.5, near = false) => {
    const rim = [], hub = [];
    for (let k = 0; k < 36; k++) {
      const a = (k / 36) * Math.PI * 2;
      rim.push(P(wx + Math.cos(a) * R, wy, 4 + R + Math.sin(a) * R));
      hub.push(P(wx + Math.cos(a) * R * 0.62, wy + 0.1, 4 + R + Math.sin(a) * R * 0.62));
    }
    mk("path", { d: poly(rim), class: near ? "sil" : "lo" }, g);
    mk("path", { d: poly(hub), class: "nf lo" }, g);
    for (let k = 0; k < 6; k++) { // spokes
      const a = (k / 6) * Math.PI * 2;
      line([wx, wy + 0.1, 4 + R], [wx + Math.cos(a) * R * 0.62, wy + 0.1, 4 + R + Math.sin(a) * R * 0.62]);
    }
    dot([wx, wy + 0.2, 4 + R], 1.1, TONE.hi);
  };
  wheel(-18, -18); wheel(18, -18);

  // the tub: a tapered solid, its foot smaller than its top (hull of two rings), one crease on the top
  const Z0 = 12, Z1 = 36;
  const foot = rrect(-25, -14, 25, 14, 4, 6), top = rrect(-31, -20, 31, 20, 5, 6), lip = rrect(-29.4, -18.4, 29.4, 18.4, 3.6, 6);
  mk("path", { d: poly(hull(ringAt(P, foot, Z0).concat(ringAt(P, top, Z1)))), class: "sil" }, g);
  mk("path", { d: open(ringAt(P, run(lip, front), Z1)), class: "nf lo" }, g);
  // strap bands down the two visible faces, and rivets along each band and under the rim
  const onY = (x, t) => [x * (1 - t) * (25 / 31) + x * t, 14 + 6 * t + 0.05, Z0 + (Z1 - Z0) * t]; // +y face, x at the top
  const onX = (y, t) => [25 + 6 * t + 0.05, y * (1 - t) * (14 / 20) + y * t, Z0 + (Z1 - Z0) * t]; // +x face
  for (const x of [-22, 0, 22]) { line(onY(x - 2, 0.04), onY(x - 2, 0.96)); line(onY(x + 2, 0.04), onY(x + 2, 0.96)); for (const t of [0.2, 0.5, 0.8]) dot(onY(x, t)); }
  for (const y of [-10, 10]) { line(onX(y - 2, 0.04), onX(y - 2, 0.96)); line(onX(y + 2, 0.04), onX(y + 2, 0.96)); for (const t of [0.2, 0.5, 0.8]) dot(onX(y, t)); }
  line(onY(-31, 0.88), onY(31, 0.88)); line(onX(-20, 0.88), onX(20, 0.88)); // the rolled rim's lower edge
  for (let x = -27; x <= 27; x += 6) dot(onY(x, 0.94), 0.55);
  for (let y = -16; y <= 16; y += 6) dot(onX(y, 0.94), 0.55);
  // axle boxes under the tub
  block(-22, 12, -14, 16, 8, 13); block(14, 12, 22, 16, 8, 13);

  // coal: a low heap, then one lump per grid cell (never intersecting), far to near
  for (const [R, z0, z1] of [[24, 35, 38], [16, 38, 41]]) { const [r, i] = rings(-R * 1.15, -R * 0.7, R * 1.15, R * 0.7, R * 0.6, 1); slab(g, K, r, i, z0, z1, "nf lo"); }
  const lumps = [], CELL = 8.2;
  for (let x = -24; x <= 24; x += CELL) for (let y = -14; y <= 14; y += CELL) {
    const n = Math.sin(x * 12.9898 + y * 78.233) * 43758.5453, j = n - Math.floor(n);
    const h = 1 - (x / 30) ** 2 - (y / 19) ** 2;
    if (h < 0.08) continue;
    lumps.push({ x, y, z: 36 + h * 8, s: CELL * (0.3 + 0.12 * j), th: 2.6 + j * 2 });
  }
  if (keep == null) {
    lumps.sort((a, b) => a.x + a.y - (b.x + b.y) || a.z - b.z);
    for (const l of lumps) block(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, l.z - l.th, l.z, "acc", 1.5, 0.6);
  } else {
    // the kept share is the rear lumps; everything else is sold and lifted
    const byX = lumps.slice().sort((a, b) => a.x - b.x), nKeep = Math.max(1, Math.round(lumps.length * keep));
    byX.forEach((l, i) => { l.sold = i >= nKeep; });
    const kept = lumps.filter((l) => !l.sold).sort((a, b) => a.x + a.y - (b.x + b.y));
    const sold = lumps.filter((l) => l.sold).sort((a, b) => a.x + a.y - (b.x + b.y));
    // where the full load used to be: one dashed outline of the heap's top
    if (lift && lift !== "ghost") mk("path", { d: poly(ringAt(P, rrect(-26, -15, 26, 15, 10, 6), 44)), class: "dash nf" }, g);
    for (const l of kept) block(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, l.z - l.th, l.z, "hi", 1.5, 0.6);
    if (lift === "ghost") { // the sold lumps stay in place as dashed accent outlines: what's gone, where it was
      for (const l of sold) {
        const [r] = rings(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, 1.5, 0.6);
        mk("path", { d: poly(hull(ringAt(P, r, l.z - l.th).concat(ringAt(P, r, l.z)))), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.75" }, g);
      }
    }
    for (const l of lift && lift !== "ghost" ? sold : []) { // lift = 0: the sold lumps are simply gone
      const z = l.z + lift + (l.x + 24) * 0.35, op = Math.max(0.35, 1 - (l.x + 24) / 70);
      const [r, i] = rings(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, 1.5, 0.6);
      slab(mk("g", { opacity: op }, g), K, r, i, z - l.th, z, "acc");
    }
    g.keptAt = [kept[0].x, kept[0].y, kept[0].z];
    if (sold.length) {
      const top = sold.reduce((a, b) => (b.x > a.x ? b : a));
      g.soldAt = lift === "ghost" ? [top.x, top.y, top.z] : [top.x, top.y, top.z + lift + (top.x + 24) * 0.35];
    }
    g.heapAt = [26, 0, 44];
  }

  // near wheels, then the near rail in front of everything
  wheel(-18, 18, 7.5, true); wheel(18, 18, 7.5, true);
  if (track) block(-42, 16, 42, 19, 1.6, 4, "sil", 0.6, 0.3);
  g.K = K; // so a slide can annotate world points on the cart
  return g;
}

// ---------------------------------------------------------------- a coal haul truck
/**
 * A mining haul truck loaded with coal, front at +x. `frame` picks the camera: "full" fits the whole truck,
 * "rear" zooms on the rear tyre and the loaded body's back corner. `clip` = [x, y, w, h] in view units.
 */
function drawHaulTruck(parent, { frame = "rear", S, cx = 196, cy = 318, clip } = {}) {
  const defs = mk("defs", {}, svg);
  let g = mk("g", {}, parent);
  if (clip) {
    const id = `clip${Math.random().toString(36).slice(2, 8)}`;
    mk("rect", { x: clip[0], y: clip[1], width: clip[2], height: clip[3] }, mk("clipPath", { id }, defs));
    g.setAttribute("clip-path", `url(#${id})`);
  }
  const K = frame === "full"
    ? camera(S ?? 1.5, [[-62, -30, 0], [68, 30, 0], [-62, -26, 60], [64, 30, 50], [0, 30, 0]], cx, cy)
    : frame === "mid" // most of the truck (rear to cab), centred, the front tip just off-frame
      ? camera(S ?? 2.05, [[-62, -26, 0], [50, 27, 0], [-60, -26, 62], [50, 26, 50]], cx, cy)
      : camera(S ?? 3.1, [[-62, 12, 0], [-8, 27, 0], [-60, 0, 62], [-8, 26, 50]], cx, cy);
  const P = K.P;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1.6, b = 1) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); return slab(g, K, ring, inner, z0, z1, cls); };
  const facePoly = (pts, cls = "nf lo") => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls }, g);

  function tyre(cx_, y0, y1, R) {
    const N = 40, A = [], B = [];
    for (let k = 0; k < N; k++) {
      const a = (k / N) * Math.PI * 2, x = cx_ + Math.cos(a) * R, z = R + Math.sin(a) * R;
      A.push([x, y0, z]); B.push([x, y1, z]);
    }
    mk("path", { d: poly(hull(A.concat(B).map((p) => P(...p)))), class: "sil" }, g);
    for (let k = 0; k < N; k += 2) { const a = (k / N) * Math.PI * 2; if (Math.cos(a) * 0.61 + Math.sin(a) * 0.5 > 0.05) line(A[k], B[k]); }
    mk("path", { d: poly(B.map((p) => P(...p))), class: "sil" }, g);
    const ring = (r) => mk("path", { d: poly(B.map(([x, , z]) => P(cx_ + (x - cx_) * r, y1 + 0.15, R + (z - R) * r))), class: "nf lo" }, g);
    ring(0.72); ring(0.5); ring(0.22);
    for (let k = 0; k < 8; k++) {
      const a = (k / 8) * Math.PI * 2, [sx, sy] = P(cx_ + Math.cos(a) * R * 0.36, y1 + 0.2, R + Math.sin(a) * R * 0.36);
      mk("circle", { cx: sx, cy: sy, r: 0.55, fill: TONE.edge }, g);
    }
  }

  mirror(g, K, rings(-60, -26, 62, 26, 4, 1)[0], 0, 14);
  floor(g, K, -90, -60, 100, 60, 10);
  tyre(-34, -27, -19, 15); tyre(-34, -18, -12, 15); tyre(40, -26, -17, 15);
  block(-52, -12, 50, -6, 13, 19); block(-52, 6, 50, 12, 13, 19);
  block(-36, -18, -32, 18, 13, 16, "nf lo"); block(38, -18, 42, 18, 13, 16, "nf lo");
  block(-60, -26, 24, 26, 19, 50, "sil", 3, 1.6);
  for (const x of [-50, -38, -26, -14, -2, 10]) line([x, 26.05, 21], [x, 26.05, 49]);
  line([-58, 26.05, 30], [22, 26.05, 30]);
  for (const yy of [-16, -6, 4, 14]) line([24.05, yy, 22], [24.05, yy, 48]);
  block(24, -26, 62, 26, 47, 50, "sil", 2, 1);
  for (const x of [32, 42, 52]) line([x, 26.05, 47.5], [x, 26.05, 49.5]);
  // the load: one lump per grid cell (never intersecting), on a low heap, painted far to near
  const CELL = 10.5, lumps = [];
  for (let x = -55; x <= 18; x += CELL) for (let yy = -21; yy <= 21; yy += CELL) {
    const nz = Math.sin(x * 12.9898 + yy * 78.233) * 43758.5453, j = nz - Math.floor(nz);
    const h = 1 - ((x + 18) / 42) ** 2 - (yy / 26) ** 2;
    if (h < 0.05) continue;
    lumps.push({ x: x + (j - 0.5) * 1.5, y: yy, z: 50 + h * 10, s: CELL * (0.32 + 0.12 * j), th: 3 + j * 2.5 });
  }
  for (const [R, z0, z1] of [[30, 48, 51.5], [22, 51.5, 54.5], [13, 54.5, 57]]) {
    const [hr, hi] = rings(-18 - R * 1.3, -R * 0.8, -18 + R * 1.3, R * 0.8, R * 0.7, 1);
    slab(g, K, hr, hi, z0, z1, "nf lo");
  }
  lumps.sort((a, b) => a.x + a.y - (b.x + b.y) || a.z - b.z);
  for (const l of lumps) block(l.x - l.s, l.y - l.s * 0.85, l.x + l.s, l.y + l.s * 0.85, l.z - l.th, l.z, "acc", 1.8, 0.7);
  // the front, kept simple: one engine hood with a short grille, one cab with two windows
  block(26, -24, 62, 24, 17, 29, "sil", 3, 1.2);                          // hood / deck as one solid
  for (let k = 0; k < 5; k++) line([62.05, -10 + k * 5, 20], [62.05, -10 + k * 5, 26]); // grille
  block(36, -22, 58, 0, 29, 46, "sil", 3, 1.2);                           // cab, under the canopy
  facePoly([[58.05, -19, 44], [58.05, -3, 44], [58.05, -3, 35], [58.05, -19, 35]]);   // windscreen
  facePoly([[39, 0.05, 44], [55, 0.05, 44], [55, 0.05, 35], [39, 0.05, 35]]);          // side window
  tyre(-34, 12, 18, 15); tyre(-34, 19, 27, 15); tyre(40, 17, 26, 15);
  return g;
}

// ---------------------------------------------------------------- one small iso icon per IDX sector
/**
 * A compact solid for each of the 11 IDX sectors, built from boxes and columns on a 60 × 60 plot, one part in
 * the accent. Parts are listed far to near (smaller x + y first) so they paint in order.
 * drawSectorIcon(parent, "Energy", { cx, cy, S }) — returns the group, or null for an unknown sector.
 */
function drawSectorIcon(parent, sector, { cx = 290, cy = 120, S = 0.9 } = {}) {
  // solids
  const box = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1.2) => ["box", x0, y0, x1, y1, z0, z1, cls, r];
  const col = (x, y, R, z0, z1, cls = "sil") => ["col", x, y, R, z0, z1, cls];
  // fine detail drawn on what is already there: a band round a box or a column at height z, a panel on a
  // camera-facing face (fy: the face at y = const, fx: at x = const), and a single line on such a face
  const bs = (x0, y0, x1, y1, z, cls = "lo") => ["bs", x0, y0, x1, y1, z, cls];
  const cs = (x, y, R, z, cls = "lo") => ["cs", x, y, R, z, cls];
  const fy = (y, x0, x1, z0, z1, cls = "lo") => ["fy", y, x0, x1, z0, z1, cls];
  const fx = (x, y0, y1, z0, z1, cls = "lo") => ["fx", x, y0, y1, z0, z1, cls];
  const ly = (y, x, z0, z1, cls = "lo") => ["ly", y, x, z0, z1, cls];
  // a free outline on a face (py: on y = const, points [x, z]; px: on x = const, points [y, z]) and a solid
  // plane through 3D points (a roof slope, a gable end), filled with the ground so it hides what is behind
  const py = (y, pts, cls = "lo") => ["py", y, pts, cls];
  const px = (x, pts, cls = "lo") => ["px", x, pts, cls];
  const p3 = (pts, cls = "sil") => ["p3", pts, cls];
  const range = (a, b, s) => { const o = []; for (let v = a; v <= b + 1e-6; v += s) o.push(v); return o; };
  // a box with floor bands every `step` up its height
  const tower = (x0, y0, x1, y1, z1, cls, step = 6) => [box(x0, y0, x1, y1, 0, z1, cls), ...range(step, z1 - 3, step).map((z) => bs(x0, y0, x1, y1, z, cls === "acc" ? "acc" : "lo")),
    ...range(x0 + 3, x1 - 5, 5).flatMap((x) => range(step / 2, z1 - 4, step).map((z) => fy(y1, x + 0.6, x + 2.6, z - 1, z + 1.6, cls === "acc" ? "acc" : "lo")))];
  const ICONS = {
    // one oil barrel: a foot ring, doubled rolling hoops (the middle pair in the accent), a label band, a rimmed
    // lid with a raised centre, a capped bung and a small vent
    "Energy": [
      col(0, 0, 18.6, 0, 2), col(0, 0, 18, 2, 46), cs(0, 0, 18.3, 4.5), cs(0, 0, 18.3, 6),
      cs(0, 0, 18.3, 15.5, "acc"), cs(0, 0, 18.3, 17, "acc"), cs(0, 0, 18.3, 21), cs(0, 0, 18.3, 27),
      cs(0, 0, 18.3, 31, "acc"), cs(0, 0, 18.3, 32.5, "acc"), cs(0, 0, 18.3, 42), cs(0, 0, 18.3, 43.5),
      col(0, 0, 18.6, 46, 48), col(0, 0, 15.5, 48, 48.8), col(-1, -1, 7, 48.8, 49.6),
      col(8, 6, 3, 48.8, 51.5), col(8, 6, 3.6, 51.5, 53, "acc"), col(-8, -7, 1.6, 48.8, 51), col(-8, -7, 2, 51, 52)],
    // a bank: three steps, a back and a front row of columns with capitals, an architrave, a stepped roof
    "Financials": [
      box(-34, -26, 34, 26, 0, 3), box(-31, -23, 31, 23, 3, 6), box(-28, -20, 28, 20, 6, 8),
      ...range(-20, 20, 10).flatMap((x) => [col(x, -12, 2.8, 8, 28), col(x, -12, 3.6, 28, 30)]),
      ...range(-20, 20, 10).flatMap((x) => [col(x, 12, 2.8, 8, 28), cs(x, 12, 2.9, 11), col(x, 12, 3.6, 28, 30)]),
      box(-29, -21, 29, 21, 30, 34), bs(-29, -21, 29, 21, 32), box(-25, -17, 25, 17, 34, 38, "acc"), box(-17, -9, 17, 9, 38, 41), box(-9, -3, 9, 3, 41, 44, "acc")],
    // a pyramid of ingots, each with a bevelled top
    "Basic Materials": [
      ...[-22, 0, 22].flatMap((x) => [box(x - 10.5, -10, x + 10.5, 10, 0, 8), box(x - 8, -7.5, x + 8, 7.5, 8, 10, "sil", 0.6)]),
      ...[-11, 11].flatMap((x) => [box(x - 10.5, -10, x + 10.5, 10, 10, 18), box(x - 8, -7.5, x + 8, 7.5, 18, 20, "sil", 0.6)]),
      box(-10.5, -10, 10.5, 10, 20, 28, "acc"), box(-8, -7.5, 8, 7.5, 28, 30, "acc", 0.6), fy(10, -5, 5, 22, 26, "acc")],
    // one milk carton: a gable top with its sealed fin, a screw cap on the front slope, a base seam, a label
    // panel with print on the front and a strip on the side
    "Consumer Non-Cyclicals": [
      box(-14, -14, 14, 14, 0, 40, "sil", 0.8), bs(-14, -14, 14, 14, 3),
      p3([[-14, -14, 40], [14, -14, 40], [14, 0, 52], [-14, 0, 52]]), p3([[-14, 14, 40], [14, 14, 40], [14, 0, 52], [-14, 0, 52]]),
      p3([[14, -14, 40], [14, 14, 40], [14, 0, 52]]), box(-14, -1, 14, 1, 52, 55, "sil", 0.3),
      fy(14, -10, 10, 10, 30, "acc"), fy(14, -7, 7, 22, 26, "acc"), ly(14, -6, 13, 13.01), py(14, [[-7, 15], [4, 15], [4, 16.4], [-7, 16.4]]), py(14, [[-7, 18], [1, 18], [1, 19.4], [-7, 19.4]]),
      fx(14, -9, 9, 26, 34), fx(14, -9, 9, 6, 10),
      col(5, 7, 3.4, 45.5, 47.5), col(5, 7, 3.4, 47.5, 50.5, "acc"), cs(5, 7, 3.5, 49, "acc")],
    // a family car (cars, retail and leisure are what people spend more on in good times): the body in the
    // accent, a sloped cabin with windows split by the pillars, door seams and a handle, headlights and a grille,
    // bumpers, a side mirror, and four wheels with rims
    "Consumer Cyclicals": [
      ["wheel", -19, -12, -8, 7.5], ["wheel", 19, -12, -8, 7.5], box(-36, -11.5, -33, 11.5, 4, 7.5, "sil", 1),
      box(-34, -11, 34, 11, 4, 17, "acc", 3), bs(-34, -11, 34, 11, 8, "acc"),
      p3([[-20, 10, 17], [16, 10, 17], [7, 10, 29], [-13, 10, 29]]), p3([[16, -10, 17], [16, 10, 17], [7, 10, 29], [7, -10, 29]]), p3([[-13, -10, 29], [7, -10, 29], [7, 10, 29], [-13, 10, 29]]),
      py(10, [[-17, 18.5], [-4, 18.5], [-4, 27.5], [-12, 27.5]]), py(10, [[-2, 18.5], [13, 18.5], [6, 27.5], [-2, 27.5]]),
      p3([[15, -8.5, 18.5], [15, 8.5, 18.5], [7.8, 8.5, 27.5], [7.8, -8.5, 27.5]], "nf lo"),
      ly(11, -3, 6, 17, "acc"), ly(11, 14, 6, 17, "acc"), py(11, [[-9, 13.5], [-5, 13.5], [-5, 14.5], [-9, 14.5]]), py(11, [[8, 13.5], [12, 13.5], [12, 14.5], [8, 14.5]]),
      fx(34, 4, 9.5, 11, 14.5), fx(34, -9.5, -4, 11, 14.5), ...[-2, 0, 2].map((y) => ["lx", 34, y, 7.5, 12]),
      box(33, -11.5, 36, 11.5, 4, 7.5, "sil", 1), box(13, 10, 16, 13.5, 17, 19.5, "sil", 0.6),
      ["wheel", -19, 8, 12, 7.5], ["wheel", 19, 8, 12, 7.5]],
    // a first-aid case: rounded shell, lid and base seams, corner bumpers, two latches, a carry handle and the
    // cross on the front in the accent (a smaller one on the side)
    "Healthcare": [
      box(-28, -15, 28, 15, 0, 32, "sil", 3), bs(-28, -15, 28, 15, 4), bs(-28, -15, 28, 15, 24), bs(-28, -15, 28, 15, 25.5),
      box(26, 13, 29, 16, 0, 32, "sil", 1.2), box(-29, 13, -26, 16, 0, 32, "sil", 1.2), box(26, -16, 29, -13, 0, 32, "sil", 1.2),
      py(15, [[-4, 6], [4, 6], [4, 10], [12, 10], [12, 18], [4, 18], [4, 22], [-4, 22], [-4, 18], [-12, 18], [-12, 10], [-4, 10]], "acc"),
      py(15, [[-20, 21], [-15, 21], [-15, 28], [-20, 28]]), py(15, [[15, 21], [20, 21], [20, 28], [15, 28]]),
      px(28, [[-2, 10], [2, 10], [2, 13], [5, 13], [5, 17], [2, 17], [2, 20], [-2, 20], [-2, 17], [-5, 17], [-5, 13], [-2, 13]], "acc"),
      box(-11, -3, -7, 3, 32, 37), box(7, -3, 11, 3, 32, 37), box(-12, -3, 12, 3, 37, 40, "sil", 1.5)],
    // a factory: a hall with a window row and a door, a saw-tooth roof, two chimneys with bands
    "Industrials": [
      col(-22, -18, 5, 0, 50), cs(-22, -18, 5.1, 40), cs(-22, -18, 5.1, 45, "acc"), col(-8, -19, 3.4, 0, 38), cs(-8, -19, 3.5, 32),
      box(-32, -8, 28, 24, 0, 20), bs(-32, -8, 28, 24, 4),
      ...range(-28, 18, 9).map((x) => fy(24, x, x + 5, 9, 15)), fx(28, 4, 14, 0, 12, "acc"),
      ...[-30, -10, 10].flatMap((x) => [box(x, -6, x + 16, 22, 20, 27, x === -30 ? "acc" : "sil", 0.6), fy(22, x + 2, x + 14, 22, 25, x === -30 ? "acc" : "lo")])],
    // a bridge: piers on footings, a deck with railings on both sides, and a lamp post
    "Infrastructures": [
      box(-28, -10, -14, 10, 0, 3), box(-26, -8, -16, 8, 3, 22), bs(-26, -8, -16, 8, 12), box(14, -10, 28, 10, 0, 3), box(16, -8, 26, 8, 3, 22), bs(16, -8, 26, 8, 12),
      box(-38, -7, 38, 7, 22, 27, "acc"), bs(-38, -7, 38, 7, 24.5, "acc"),
      ...range(-34, 34, 6).map((x) => col(x, -6, 0.6, 27, 31)), box(-36, -6.6, 36, -5.4, 31, 32, "sil", 0.3),
      col(-30, -2, 0.9, 27, 42), box(-32, -3.2, -26, -0.8, 42, 44, "acc", 0.5),
      ...range(-34, 34, 6).map((x) => col(x, 6, 0.6, 27, 31)), box(-36, 5.4, 36, 6.6, 31, 32, "sil", 0.3)],
    // three towers with floor bands and windows, the tallest in the accent with a crown, and a tree
    "Properties & Real Estate": [
      ...tower(-30, -30, -10, -10, 36), ...tower(2, -28, 22, -8, 26), ...tower(-14, 2, 8, 24, 50, "acc"), box(-10, 6, 4, 20, 50, 53, "acc"), col(-3, 13, 1, 53, 60, "acc"),
      ...tower(14, 8, 28, 22, 16, "sil", 5), col(26, 28, 1, 0, 6), col(26, 28, 5, 6, 14)],
    // a chip: a package with six pins a side, two caps on it, and a die with a grid
    "Technology": [
      ...range(-15, 15, 6).flatMap((v) => [box(v - 1.6, -31, v + 1.6, -25, 0, 2, "sil", 0.4), box(-31, v - 1.6, -25, v + 1.6, 0, 2, "sil", 0.4)]),
      box(-25, -25, 25, 25, 0, 6), bs(-25, -25, 25, 25, 3),
      ...range(-15, 15, 6).flatMap((v) => [box(v - 1.6, 25, v + 1.6, 31, 0, 2, "sil", 0.4), box(25, v - 1.6, 31, v + 1.6, 0, 2, "sil", 0.4)]),
      box(-21, 14, -15, 20, 6, 9, "sil", 0.6), box(14, -21, 20, -15, 6, 9, "sil", 0.6),
      box(-12, -12, 12, 12, 6, 10, "acc"), box(-9, -9, 9, 9, 10, 11.5, "acc", 0.6), fy(12, -9, 9, 7, 9, "acc")],
    // stacked shipping containers with ribbed sides and door bars, the top one in the accent
    "Transportation & Logistic": [
      box(-34, -14, 2, 4, 0, 15), box(4, -14, 36, 4, 0, 15),
      box(-34, 8, 36, 26, 0, 15), ...range(-30, 26, 4).map((x) => ly(26, x, 1.5, 13.5)), fx(36, 10, 24, 1.5, 13.5), ly(26, 32, 1.5, 13.5),
      box(-18, -8, 22, 12, 15, 30, "acc"), ...range(-14, 18, 4).map((x) => ly(12, x, 16.5, 28.5, "acc")), fx(22, -6, 10, 16.5, 28.5, "acc")],
  };
  const parts = ICONS[sector];
  if (!parts) return null;
  const g = mk("g", {}, parent);
  const K = camera(S, [[-38, -32, 0], [38, 32, 0], [-38, -32, 54], [38, 32, 54]], cx, cy);
  floor(g, K, -46, -46, 46, 46, 7);
  const line = (d, cls) => mk("path", { d, class: "nf thin", style: `stroke:${cls === "acc" ? "var(--acc)" : TONE.mid};stroke-width:.8px` }, g);
  for (const p of parts) {
    const [kind, ...a] = p;
    if (kind === "box") { const [x0, y0, x1, y1, z0, z1, cls, r] = a; const [ring, inner] = rings(x0, y0, x1, y1, r, Math.min(0.6, r / 2)); slab(g, K, ring, inner, z0, z1, cls); }
    else if (kind === "col") { const [x, y, R, z0, z1, cls] = a; const [ring, inner] = disc(x, y, R, Math.min(1.2, R / 3)); slab(g, K, ring, inner, z0, z1, cls); }
    else if (kind === "bs") { const [x0, y0, x1, y1, z, cls] = a; line(seam(K, rings(x0, y0, x1, y1, 1.2, 0.6)[0], z), cls); }
    else if (kind === "cs") { const [x, y, R, z, cls] = a; line(seam(K, disc(x, y, R)[0], z), cls); }
    else if (kind === "fy") { const [y, x0, x1, z0, z1, cls] = a; line(poly([K.P(x0, y, z0), K.P(x1, y, z0), K.P(x1, y, z1), K.P(x0, y, z1)]), cls); }
    else if (kind === "fx") { const [x, y0, y1, z0, z1, cls] = a; line(poly([K.P(x, y0, z0), K.P(x, y1, z0), K.P(x, y1, z1), K.P(x, y0, z1)]), cls); }
    else if (kind === "wheel") { // a tyre on an axle along y (as the haul truck's): tread, outer face, rim rings, hub
      const [wx, y0, y1, R] = a, N = 36, A = [], B = [];
      for (let k = 0; k < N; k++) { const t = (k / N) * Math.PI * 2; A.push([wx + Math.cos(t) * R, y0, R + Math.sin(t) * R]); B.push([wx + Math.cos(t) * R, y1, R + Math.sin(t) * R]); }
      mk("path", { d: poly(hull(A.concat(B).map((q) => K.P(...q)))), class: "sil" }, g);
      mk("path", { d: poly(B.map((q) => K.P(...q))), class: "sil" }, g);
      for (const r of [0.62, 0.3]) line(poly(B.map(([x, , z]) => K.P(wx + (x - wx) * r, y1 + 0.1, R + (z - R) * r))), "lo");
    }
    else if (kind === "lx") { const [x, y, z0, z1, cls = "lo"] = a; const [p0, p1] = [K.P(x, y, z0), K.P(x, y, z1)]; line(`M${p0[0]} ${p0[1]}L${p1[0]} ${p1[1]}`, cls); }
    else if (kind === "rope") { // a rope handle: an arch in the plane y, centred on x, from height z, w half-wide, h tall
      const [y, x, z, w, h] = a, pts = range(0, 1, 1 / 24).map((t) => K.P(x + w * Math.cos(Math.PI * (1 - t)), y, z + h * Math.sin(Math.PI * t)));
      const d = `M${pts.map((p) => p.join(" ")).join("L")}`;
      mk("path", { d, class: "nf", style: `stroke:${TONE.ground};stroke-width:3.4px` }, g);
      mk("path", { d, class: "nf sil", style: "stroke-width:1.6px" }, g);
    }
    else if (kind === "py") { const [y, pts, cls] = a; line(poly(pts.map(([x, z]) => K.P(x, y, z))), cls); }
    else if (kind === "px") { const [x, pts, cls] = a; line(poly(pts.map(([y, z]) => K.P(x, y, z))), cls); }
    else if (kind === "p3") { const [pts, cls] = a; mk("path", { d: poly(pts.map(([x, y, z]) => K.P(x, y, z))), class: cls }, g); }
    else if (kind === "ly") { const [y, x, z0, z1, cls] = a; const [p0, p1] = [K.P(x, y, z0), K.P(x, y, z1)]; line(`M${p0[0]} ${p0[1]}L${p1[0]} ${p1[1]}`, cls); }
  }
  return g;
}
