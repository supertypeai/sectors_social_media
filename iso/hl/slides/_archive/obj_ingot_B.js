// Basic Materials · ingot pallet, style "B · minimal": a plain pallet and 16 big trapezoid ingots in three
// courses (6 · 6 · 4). No trim. Hook slide reuses byan_variants VARIANTS[10]'s layout.
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * drawIngotPallet_B — OBJECTS.md §1 contract. keep splits top-to-bottom: the kept ingots are the bottom
 * course(s), the gone ones sit above as dashed accent ghosts where they used to be.
 */
function drawIngotPallet_B(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const block = (x0, y0, x1, y1, z0, z1, cls = "sil", r = 1, b = 0.5) => { const [ring, inner] = rings(x0, y0, x1, y1, r, b); slab(g, K, ring, inner, z0, z1, cls); };

  // 1 · floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 2 · behind the deck: three skids along x
  for (const y of [-21, 0, 21]) block(-46, y - 3.5, 46, y + 3.5, 0, 5, "sil", 0.8, 0.4);
  // 3 · the deck: one slab
  block(-48, -25, 48, 25, 5, 8.5, "sil", 1.2, 0.6);

  // 5 · the load: trapezoid ingots, foot wider than top; courses of height H
  const H = 11, Z = 8.5, units = [];
  const course = (z, xs, ys) => { for (const x of xs) for (const y of ys) units.push({ x, y, z0: z, z1: z + H }); };
  course(Z, [-22.5, 22.5], [-16.5, 0, 16.5]);
  course(Z + H, [-22.5, 22.5], [-16.5, 0, 16.5]);
  course(Z + 2 * H, [-22.5, 22.5], [-8.25, 8.25]);
  const HX = 21, HY = 7.3, IN = 2.6; // half length, half width, top inset
  const shape = (u) => {
    const foot = rrect(u.x - HX, u.y - HY, u.x + HX, u.y + HY, 1.2, 4);
    const top = rrect(u.x - HX + IN, u.y - HY + IN * 0.6, u.x + HX - IN, u.y + HY - IN * 0.6, 1, 4);
    return { foot, top };
  };
  const ingot = (u, cls) => {
    const { foot, top } = shape(u);
    mk("path", { d: poly(hull(ringAt(P, foot, u.z0).concat(ringAt(P, top, u.z1)))), class: cls }, g);
    mk("path", { d: poly(ringAt(P, top, u.z1)), class: "nf lo" }, g); // the top face: one crease
  };
  const ghostIngot = (u) => {
    const { foot, top } = shape(u);
    const ds = "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;stroke-opacity:.9";
    mk("path", { d: poly(hull(ringAt(P, foot, u.z0).concat(ringAt(P, top, u.z1)))), style: `fill:${TONE.ground};${ds}` }, g);
    mk("path", { d: poly(ringAt(P, top, u.z1)), class: "nf", style: `${ds};stroke-opacity:.4` }, g);
  };
  const order = (a, b) => a.z0 - b.z0 || a.x + a.y - (b.x + b.y);
  units.sort(order);
  if (keep == null) {
    for (const u of units) ingot(u, "acc");
  } else {
    // split top-to-bottom: keep the bottom course first, and inside a course the near ingots first,
    // so what stayed is never hidden behind what went
    const nKeep = Math.max(1, Math.round(units.length * keep));
    const rank = units.slice().sort((a, b) => a.z0 - b.z0 || b.x + b.y - (a.x + a.y));
    rank.forEach((u, i) => { u.gone = i >= nKeep; });
    const kept = units.filter((u) => !u.gone), gone = units.filter((u) => u.gone);
    // ghosts are ground-filled and painted in the same far-to-near order, so the gone stack reads as one
    // calm dashed solid instead of a tangle of see-through outlines
    for (const u of units) {
      if (!u.gone) ingot(u, "hi");
      else if (lift === "ghost") ghostIngot(u);
    }
    const kt = kept.reduce((a, b) => (b.z1 > a.z1 || (b.z1 === a.z1 && b.x + b.y > a.x + a.y) ? b : a));
    g.keptAt = [kt.x - 6, kt.y + HY, (kt.z0 + kt.z1) / 2]; // on its near face: never under a ghost
    if (gone.length) { const top = gone.at(-1); g.soldAt = [top.x, top.y, top.z1]; }
  }
  const topZ = Z + 3 * H;
  g.K = K;
  g.anchor = { load: [0, 0, topZ], base: [48, 25, 5], kept: g.keptAt ?? [0, 0, topZ] };
  return g;
}

// ---------------------------------------------------------------- hook (VARIANTS[10] layout)
const stat = (g, x, yy, k, v, accent = false) => {
  type(g, x, yy, k, "caps", { fill: TONE.faint, size: 5.6 });
  type(g, x, yy + 18, v, "num", { size: 19, weight: 280, fill: accent ? "var(--acc)" : TONE.hi });
};
frame(D);
para(svg, M, 74, `Why would ${S.holder} sell 30% of Bayan in a single day?`, "title", { accent: ["30%"], maxW: W - 2 * M });
const keep = S.keepOverride ?? S.after / S.before;
const obj = drawIngotPallet_B(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: "ghost" });
const P = obj.K.P;
if (keep < 1) leader(svg, P(...(obj.soldAt ?? obj.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...obj.anchor.kept), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
