// Basic Materials · "the stake is the ingots": no pallet, no container. Standalone trapezoid ingots stand
// on the floor in a tidy 4 × 5 iso grid (20 units). The split runs left-to-right by column: kept ingots are the left
// columns (solid, bright), sold ones stay in place as dashed accent ghosts. Hook = VARIANTS[10] layout.
const D = DATA, S = D.slide;
setAccent(D.direction);

/**
 * drawIngotField — OBJECTS.md §1 contract. N = COLS*ROWS identical ingots; kept count = round(keep*N),
 * filled column by column from the left (inside a column, near ingots first).
 */
function drawIngotField(parent, { S, cx, cy, floorOn = true, keep = null, lift = "ghost" } = {}) {
  const g = mk("g", {}, parent);
  // same model box as the ingot pallet (and cart family) so scale matches
  const K = camera(S, [[-50, -26, 0], [50, 26, 0], [-32, -20, 46], [32, 20, 46]], cx, cy);
  const P = K.P;
  if (floorOn) floor(g, K, -80, -50, 80, 50, 8);

  const COLS = 4, ROWS = 5, SX = 25, SY = 11.5, H = 7.5;
  const HX = 11, HY = 4.4, IN = 1.9;
  const units = [];
  for (let c = 0; c < COLS; c++) for (let r = 0; r < ROWS; r++)
    units.push({ c, r, x: (c - (COLS - 1) / 2) * SX, y: (r - (ROWS - 1) / 2) * SY, z0: 0, z1: H });
  const shape = (u) => ({
    foot: rrect(u.x - HX, u.y - HY, u.x + HX, u.y + HY, 1.2, 4),
    top: rrect(u.x - HX + IN, u.y - HY + IN * 0.6, u.x + HX - IN, u.y + HY - IN * 0.6, 1, 4),
  });
  const ingot = (u, cls) => {
    const { foot, top } = shape(u);
    mk("path", { d: poly(hull(ringAt(P, foot, u.z0).concat(ringAt(P, top, u.z1)))), class: cls }, g);
    mk("path", { d: poly(ringAt(P, top, u.z1)), class: "nf lo" }, g);
  };
  const ghostIngot = (u) => {
    const { foot, top } = shape(u);
    const ds = "stroke:var(--acc);stroke-dasharray:2 2.5;stroke-width:1px;stroke-opacity:.75";
    mk("path", { d: poly(hull(ringAt(P, foot, u.z0).concat(ringAt(P, top, u.z1)))), style: `fill:${TONE.ground};${ds}` }, g);
    mk("path", { d: poly(ringAt(P, top, u.z1)), class: "nf", style: `${ds};stroke-opacity:.35` }, g);
  };
  // painter: far (small x+y) to near
  units.sort((a, b) => a.x + a.y - (b.x + b.y));
  if (keep == null) {
    for (const u of units) ingot(u, "acc");
  } else {
    const nKeep = Math.max(1, Math.min(units.length, Math.round(units.length * keep)));
    const rank = units.slice().sort((a, b) => a.c - b.c || b.r - a.r);
    rank.forEach((u, i) => { u.gone = i >= nKeep; });
    for (const u of units) {
      if (!u.gone) ingot(u, "hi");
      else if (lift === "ghost") ghostIngot(u);
    }
    const kept = units.filter((u) => !u.gone), gone = units.filter((u) => u.gone);
    // kept anchor: front-left-most kept ingot's near face; sold anchor: top of the far-right ghost
    const kt = kept.reduce((a, b) => (b.y - b.x > a.y - a.x ? b : a));
    g.keptAt = [kt.x, kt.y + HY, H / 2];
    if (gone.length) { const t = gone.reduce((a, b) => (b.x - b.y > a.x - a.y ? b : a)); g.soldAt = [t.x, t.y, H]; }
  }
  g.K = K;
  g.anchor = { load: [0, 0, H], base: [50, 26, 0], kept: g.keptAt ?? [0, 0, H], sold: g.soldAt ?? null };
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
const obj = drawIngotField(svg, { S: 2.2, cx: 182, cy: 266, keep, lift: "ghost" });
const P = obj.K.P;
if (keep < 1) leader(svg, P(...(obj.anchor.sold ?? obj.anchor.load)), [W - M - 64, 160], [[`${S.sold.pct.toFixed(1)}% sold`, "label", { fill: "var(--acc)", weight: 700, size: 12 }], [S.day, "label", { fill: TONE.muted, size: 7 }]], { cls: "dash nf acc" });
leader(svg, P(...obj.anchor.kept), [M + 64, 196], [[`${S.after.toFixed(2)}% kept`, "label", { fill: TONE.hi, weight: 650, size: 11 }], ["what's left", "label", { fill: TONE.muted, size: 6.8 }]], { anchor: "end" });
const s = mk("g", {}, svg), Y = H - 66;
mk("line", { x1: M, y1: Y - 12, x2: W - M, y2: Y - 12, class: "lo thin" }, s);
stat(s, M, Y, "STAKE BEFORE", `${S.before.toFixed(2)}%`);
stat(s, M + 108, Y, "STAKE AFTER", `${S.after.toFixed(2)}%`);
stat(s, M + 214, Y, `VALUE · ${S.day.toUpperCase()}`, S.value, true);
