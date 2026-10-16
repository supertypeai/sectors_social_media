// Consumer Non-Cyclicals object, style A (faithful): a slatted produce crate filled with cans.
// Hook slide reuses byan_variants VARIANTS[10]'s layout. DATA.slide.keepOverride forces `keep`.

/**
 * A slatted crate on two skids, filled with 18 cans (3 rows × 6). Parts: skids, body, corner posts,
 * slats + nails, hand slot, cans. Kept cans = rear (low x); gone cans = dashed accent ghosts.
 * lift: "ghost" (sell) or "add" (buy: the added cans drawn solid in the accent).
 */
function drawGroceryCrate_A(parent, { S = 2.2, cx = 182, cy = 266, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1, b = 0.5) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };
  const dot = (p, r = 0.7, fill = TONE.edge) => { const [x, y] = P(...p); mk("circle", { cx: x, cy: y, r, fill }, g); };
  const face = (pts, cls = "sil") => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls }, g);

  const X = 34, Y = 21, Z0 = 3, Z1 = 33; // body box
  // 1. floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2. skids under the body
  block(-X, -17, X, -13, 0, Z0, "sil", 0.6, 0.3);
  block(-X, 13, X, 17, 0, Z0, "sil", 0.6, 0.3);
  // 3. body silhouette, and the open top (inner rim)
  block(-X, -Y, X, Y, Z0, Z1, "sil", 1.2, 0.6);
  face([[-X + 2.4, -Y + 2.4, Z1], [X - 2.4, -Y + 2.4, Z1], [X - 2.4, Y - 2.4, Z1], [-X + 2.4, Y - 2.4, Z1]], "lo");

  // 5. the cans: one per grid cell, far to near
  const cans = [];
  for (let x = -27.5; x <= 27.5; x += 11) for (const y of [-12, 0, 12]) cans.push({ x, y });
  const R = 4.6, CZ0 = 25, CZ1 = 40;
  const nKeep = keep == null ? cans.length : Math.max(1, Math.round(cans.length * keep));
  cans.slice().sort((a, b) => a.x - b.x || a.y - b.y).forEach((c, i) => { c.gone = i >= nKeep; });
  const order = (a, b) => a.x + a.y - (b.x + b.y);
  const kept = cans.filter((c) => !c.gone).sort(order), gone = cans.filter((c) => c.gone).sort(order);
  const can = (c, cls) => { const [r, i] = disc(c.x, c.y, R, 0.9, 40); slab(g, K, r, i, CZ0, CZ1, cls); };
  for (const c of kept) can(c, keep == null ? "sil" : "hi");
  if (lift === "add") for (const c of gone) can(c, "acc");

  // 4. near walls over the can bottoms, with slats, posts and nails (one rhythm)
  face([[-X, Y, Z0], [X, Y, Z0], [X, Y, Z1], [-X, Y, Z1]]);
  face([[X, -Y, Z0], [X, Y, Z0], [X, Y, Z1], [X, -Y, Z1]]);
  const gaps = [13, 23], nails = [8, 18, 28];
  for (const z of gaps) for (const dz of [-0.9, 0.9]) {
    line([-X + 4, Y + 0.05, z + dz], [X - 4, Y + 0.05, z + dz]);
    line([X + 0.05, -Y + 4, z + dz], [X + 0.05, Y - 4, z + dz]);
  }
  for (const s of [-1, 1]) { // corner posts
    line([s * (X - 4), Y + 0.05, Z0], [s * (X - 4), Y + 0.05, Z1]);
    line([X + 0.05, s * (Y - 4), Z0], [X + 0.05, s * (Y - 4), Z1]);
    for (const z of nails) { dot([s * (X - 2), Y + 0.1, z]); dot([X + 0.1, s * (Y - 2), z]); }
  }
  // hand slot on the short face
  const slot = [];
  for (let k = 0; k < 24; k++) { const a = (k / 24) * Math.PI * 2; slot.push(P(X + 0.1, Math.cos(a) * 7, 28 + Math.sin(a) * 1.6)); }
  mk("path", { d: poly(slot), class: "nf lo" }, g);
  // near rim edge highlight
  line([-X + 1, Y, Z1], [X, Y, Z1], "nf hi"); line([X, Y, Z1], [X, -Y + 1, Z1], "nf hi");

  // 6. ghosts of the gone cans, last and on top (only the part above the rim)
  if (lift === "ghost") for (const c of gone) {
    const A = [], B = [];
    for (let k = 0; k < 40; k++) { const a = (k / 40) * Math.PI * 2; A.push(P(c.x + Math.cos(a) * R, c.y + Math.sin(a) * R, Z1)); B.push(P(c.x + Math.cos(a) * R, c.y + Math.sin(a) * R, CZ1)); }
    mk("path", { d: poly(hull(A.concat(B))) + poly(B), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.75" }, g);
  }

  g.K = K;
  g.anchor = { load: [0, 0, CZ1], base: [X, Y, Z0] };
  return g;
}

// ---------------------------------------------------------------- hook slide (VARIANTS[10] layout)
{
  const D = DATA, S = D.slide;
  setAccent(D.direction);
  const keep = S.keepOverride ?? S.after / S.before;
  const buy = D.direction === "buy";
  const stat = (g, x, yy, k, v, accent = false) => {
    type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
    type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
  };
  frame(D);
  para(svg, M, 74, `Why would ${S.holder} ${buy ? "buy" : "sell"} 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
  const obj = drawGroceryCrate_A(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: buy ? "add" : "ghost" });
  const P = obj.K.P;
  leader(svg, P(...obj.anchor.load), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% ${buy ? "bought" : "sold"}`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
  leader(svg, P(...obj.anchor.base), [M + 64, 340], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
  const s = mk("g", {}, svg), Y = H - 66;
  mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
  stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
  stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
  stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
}
