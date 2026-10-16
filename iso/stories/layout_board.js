// Layout B, "chart on a board": the chart is a normal chart, painted on the front of a board standing
// in the scene, with the insider(s) in front of it. Stat tiles sit flat underneath.
const D = DATA, ACC = accentOf(D);
const BW = 120, BH = 66, BY = -14, BZ = 14; // the board: width along x, height, its plane, its foot
const legs = [-48, 48].map((x, i) => body(`leg-${i}`, () => ({ x, y: BY, z: 2, w: 3, d: 3, h: BZ, r: 1, b: 0.4, layer: 1, color: "#3a3431", tone: "hi" })));
const board = body("board", () => ({ x: 0, y: BY, z: BZ, w: BW, d: 3, h: BH, r: 1.6, b: 0.8, layer: 1, color: "#26211e", side: "#1f1b19", tone: "hi" }));
const n = D.kind === "cluster" ? Math.min(4, D.scene.people.length) : 1;
const spots = [[-34, 20], [-14, 24], [6, 24], [26, 20]].slice(0, n);
const people = spots.flatMap(([x, y], i) => person(`p-${i}`, () => ({ x, y, z: 2, k: 1.5, color: i === 0 ? ACC : "#8a817a", tone: i === 0 ? "hi" : "base", opacity: 1 })));
const plate = body("plate", () => ({ x: 0, y: 4, z: 0, w: BW + 20, d: 56, h: 2, r: 3, b: 1, layer: 0, color: "#1f1b19", side: "#151210", tone: "hi" }));

export default feedStory({
  name: "layout-board", D, accent: ACC,
  bodies: [plate, ...legs, board, ...people],
  bounds: [[-(BW + 20) / 2, -24, 0], [(BW + 20) / 2, 32, 0], [-BW / 2, BY, BZ + BH], [BW / 2, BY, BZ + BH], [-(BW + 20) / 2, 32, 0], [(BW + 20) / 2, -24, 0]],
  band: { top: 0.37, bottom: 0.795, width: 0.94 },
  overlay: (P, view) => {
    // the chart, drawn at 2× in a 236 × 124 box, then laid on the board's front face
    const face = faceMatrix(P, [-BW / 2 + 2, BY + 1.55, BZ + BH - 2]);
    const chart = rect(0, 0, 236, 128, { fill: "#2a2421", r: 3 }) +
      txt(10, 15, D.chart.title.toUpperCase(), { size: 8, weight: 650, fill: SUBTLE, ls: 0.6 }) +
      chartOf(D.chart, 10, 24, 216, 88, ACC);
    const ty = view.h * 0.815;
    return `<g transform="${face}"><g transform="scale(0.5)">${chart}</g></g>` +
      tiles(D.tiles, 16, ty, view.w - 32, view.h * 0.105, ACC) + footer(view, D);
  },
});
