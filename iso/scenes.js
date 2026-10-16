// Iso vignettes for feed posts. They tell WHO did WHAT to WHICH company; the numbers live in the flat
// overlay, so nothing here has to be read as a chart. Each scene returns { bodies, bounds, signs(P) }:
// bounds are world points for sceneFit, signs(P) is overlay SVG painted onto faces (the ticker on the tower).
// post.mjs pastes this file after parts.js.

/** The company: an office tower on a plate, with the ticker on a sign across its front face. */
function companyTower(id, at, { h = 66, w = 30, d = 26, tint = "#8f8780", side = "#6b645e" } = {}) {
  const b = body(id, () => ({ x: at.x, y: at.y, z: 2, w, d, h, r: 1.5, b: 1, layer: 1, color: tint, side, tone: "hi", marks: towerMarks }));
  // the sign stands proud of the roof line, so the ticker is the first thing read on the building
  const SW = w + 4, SH = 13, SZ = 2 + h - 4;
  const sign = body(`${id}-sign`, () => ({ x: at.x, y: at.y + d / 2 + 0.8, z: SZ, w: SW, d: 1.6, h: SH, r: 0.6, b: 0.4, layer: 2, color: "#1f1b19", side: "#151210", tone: "hi" }));
  const signAt = (P, ticker, accent) => {
    const o = [at.x - SW / 2, at.y + d / 2 + 1.65, SZ + SH];
    return `<g transform="${faceMatrix(P, o)}">${txt(SW / 2, SH / 2 + 3.4, ticker, { size: 9.5, weight: 800, head: true, anchor: "middle", fill: accent, ls: 0.3 })}</g>`;
  };
  return { bodies: [b, sign], top: [at.x, at.y, SZ + SH + 1], signAt };
}
const plateOf = (id, w, d) => body(id, () => ({ x: 0, y: 0, z: 0, w, d, h: 2, r: 3, b: 1, layer: 0, color: "#1f1b19", side: "#151210", tone: "hi" }));
const stackOf = (id, x, y, h, hi) => body(id, () => ({ x, y, z: 2, w: 12, d: 8, h, r: 0.8, b: 0.6, layer: 2,
  color: hi ? NOTE : "#7f9e7c", side: hi ? NOTE_S : "#5b7558", tone: hi ? "accent" : "base", marks: bundleMarks(Math.min(5, h), true) }));
const plateBounds = (w, d) => [-1, 1].flatMap((sx) => [-1, 1].map((sy) => [sx * w / 2, sy * d / 2, 0]));

/** One insider and one company: small trades in a row, the outsized one stacked tall. Selling walks the money away. */
function chainScene(D, accent) {
  const sell = D.direction === "sell";
  const tower = companyTower("co", { x: 26, y: -12 });
  const person1 = person("insider", () => ({ x: sell ? -46 : -40, y: 14, z: 2, k: 1.7, color: accent, tone: "hi", opacity: 1 }));
  // the money between them: three ordinary bundles and the big one by the receiving side
  const smalls = [-22, -12, -2].map((x, i) => stackOf(`small-${i}`, x, 14, 2.6 + i * 0.4, false));
  const big = stackOf("big", sell ? -28 : 12, sell ? -6 : 16, 26, true);
  return {
    bodies: [plateOf("plate", 128, 72), ...tower.bodies, ...person1, ...smalls, big],
    bounds: [...plateBounds(128, 72), tower.top, [-40, 14, 44], [12, 16, 30]],
    signs: (P) => tower.signAt(P, D.symbol, accent),
  };
}

/** Several insiders and one company: the biggest trader in accent with the big stack, the rest in stone. */
function clusterScene(D, accent) {
  const tower = companyTower("co", { x: 18, y: -18 });
  const names = D.scene.people; // biggest first
  const slots = [[-30, 20], [-48, 6], [-12, 26], [-56, -10], [4, 28]].slice(0, names.length);
  const people = slots.flatMap(([x, y], i) => person(`p-${i}`, () => ({ x, y, z: 2, k: 1.45, color: i === 0 ? accent : "#8a817a", tone: i === 0 ? "hi" : "base", opacity: 1 })));
  const stacks = slots.map(([x, y], i) => stackOf(`s-${i}`, x + 9, y + 1, i === 0 ? 24 : 2.6, i === 0));
  return {
    bodies: [plateOf("plate", 140, 80), ...tower.bodies, ...people, ...stacks],
    bounds: [...plateBounds(140, 80), tower.top, [-30, 20, 40], [-21, 21, 28]],
    signs: (P) => tower.signAt(P, D.symbol, accent),
  };
}

const sceneFor = (D, accent) => (D.kind === "cluster" ? clusterScene : chainScene)(D, accent);

/**
 * A still feed slide: header text from DATA.copy at the top, the bodies fitted into [band.top, band.bottom],
 * and overlay(P, view) painted flat over everything. P projects world points to the view, so overlay
 * text can sit on the drawing.
 */
function feedStory({ name, D, accent, bodies, bounds, band, overlay }) {
  const camFit = sceneFit(bounds, band);
  OVERLAY((view) => overlay(projector(camFit(view), view), view));
  return ISO.story({
    name, duration: 1, aspect: "4:5", backdrop: "grid", poster: 0.9,
    theme: { ...SECTORS_THEME, accent }, brand: { name: "Sectors", accent, font: "\"Inter Tight\", Inter, ui-sans-serif, system-ui, sans-serif" },
    bodies,
    camera: (t, { view }) => camFit(view),
    texts: [
      { t0: 0, text: D.copy.kicker, style: "kicker", at: "top", group: "head", anim: "none" },
      { t0: 0, text: D.copy.headline, style: "big", group: "head", anim: "none", emphasis: D.copy.emphasis },
      { t0: 0, text: D.copy.sub, style: "title", group: "head", anim: "none" },
    ],
  });
}
const accentOf = (D) => (D.direction === "sell" ? SECTORS.rose : SECTORS.teal);
/** The source line and the site, at the very bottom of every slide. */
const footer = (view, D) => txt(18, view.h - 12, D.copy.source, { size: 6.6, fill: SUBTLE }) + txt(view.w - 18, view.h - 12, "sectors.app", { size: 6.6, weight: 650, fill: SECTORS.muted, anchor: "end" });
