// Consumer Non-Cyclicals: a grocery crate of cans, "B · minimal" — a plain slatted box, one slat gap per
// face, 12 big cans standing in it. DATA.slide.keepOverride forces keep (for the 4-up review renders).
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * A slatted produce crate holding a 5 × 3 grid of cans. Painted far to near: floor, crate body, slat gaps,
 * cans (kept bright / sold dashed / bought solid accent), then the crate's two near walls over the can feet.
 */
function drawGroceryCrate_B(parent, { S = 2.2, cx = 182, cy = 266, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  const X = 37, Y = 21, Z1 = 30;                   // crate half-extents and rim height
  const quad = (pts, cls) => mk("path", { d: poly(pts.map((p) => P(...p))), class: cls }, g);
  const line = (a, b, cls = "nf lo") => mk("path", { d: `M${P(...a).join(" ")}L${P(...b).join(" ")}`, class: cls }, g);

  // 1 floor
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);
  // 3 body: one box silhouette, the open top's inner rim as a crease
  const [box, boxIn] = rings(-X, -Y, X, Y, 2, 1);
  slab(g, K, box, boxIn, 0, Z1, "sil");
  mk("path", { d: poly(ringAt(P, rrect(-X + 3, -Y + 3, X - 3, Y - 3, 1.5, 4), Z1)), class: "nf lo" }, g);

  // 5 load: cans on a grid, rear (−x) first is what's kept
  const R = 6.8, ZB = Z1 - 8, ZT = Z1 + 10;
  const cans = [];
  for (const x of [-24, -8, 8, 24]) for (const y of [-12, 0, 12]) cans.push({ x, y });
  const n = cans.length, nKeep = keep == null ? n : Math.max(0, Math.min(n, Math.round(n * keep)));
  cans.slice().sort((a, b) => a.x - b.x || a.y - b.y).forEach((c, i) => { c.gone = i >= nKeep; });
  cans.sort((a, b) => a.x + a.y - (b.x + b.y));
  const can = (c, cls) => { const [r, i] = disc(c.x, c.y, R, 1.4, 40); slab(g, K, r, i, ZB, ZT, cls); };
  const ghostCan = (c) => {
    const [r] = disc(c.x, c.y, R, 1.4, 40);
    mk("path", { d: poly(hull(ringAt(P, r, ZB).concat(ringAt(P, r, ZT)))), class: "nf", style: "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1.1px;opacity:.75" }, g);
  };
  for (const c of cans) {
    if (!c.gone) can(c, keep == null ? "sil" : "hi");
    else if (lift === "add") can(c, "acc");
  }
  // 6 ghost: the sold cans, dashed where they stood
  if (lift === "ghost") for (const c of cans) if (c.gone) ghostCan(c);

  // 7 near walls over the can feet, with one slat gap each (the crate's only rhythm)
  quad([[-X, Y, 0], [X, Y, 0], [X, Y, Z1], [-X, Y, Z1]], "sil");
  quad([[X, -Y, 0], [X, Y, 0], [X, Y, Z1], [X, -Y, Z1]], "sil");
  for (const z of [Z1 * 0.5]) { line([-X + 2, Y + 0.05, z], [X - 2, Y + 0.05, z]); line([X + 0.05, -Y + 2, z], [X + 0.05, Y - 2, z]); }
  line([X + 0.05, -6, Z1 - 6], [X + 0.05, 6, Z1 - 6], "nf sil");   // the end handle slot

  const kept = cans.filter((c) => !c.gone), gone = cans.filter((c) => c.gone);
  if (kept.length) { const k = kept.reduce((a, b) => (b.x + b.y < a.x + a.y ? b : a)); g.keptAt = [k.x, k.y, ZT]; }
  if (gone.length) { const t = gone.reduce((a, b) => (b.x + b.y > a.x + a.y ? b : a)); g.goneAt = [t.x, t.y, ZT]; }
  g.K = K;
  g.anchor = { load: [0, 0, ZT], base: [X, Y, 0] };
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
const obj = drawGroceryCrate_B(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: D.direction === "buy" ? "add" : "ghost" });
const P = obj.K.P;
leader(svg, P(...(obj.goneAt ?? obj.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...(obj.keptAt ?? obj.anchor.base)), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
