// Layout C, "numbers on plinths": the three key numbers are cut into the fronts of iso plinths, the
// hero one tallest; the insider(s) stand beside them; a flat chart strip underneath.
const D = DATA, ACC = accentOf(D);
const XS = [-54, 0, 54], PW = 48, PD = 30;
const hero = Math.max(0, D.tiles.findIndex((t) => t.tone === "accent"));
const PH = XS.map((_, i) => (i === hero ? 40 : 32));
const plinths = XS.map((x, i) => body(`plinth-${i}`, () => ({ x, y: 0, z: 2, w: PW, d: PD, h: PH[i], r: 2, b: 0.8, layer: 1,
  color: i === hero ? "#3a3431" : "#2c2724", side: i === hero ? "#2a2522" : "#211d1b", tone: i === hero ? "accent" : "hi" })));
const plate = body("plate", () => ({ x: 10, y: 6, z: 0, w: 206, d: 66, h: 2, r: 3, b: 1, layer: 0, color: "#1f1b19", side: "#151210", tone: "hi" }));
const n = D.kind === "cluster" ? Math.min(3, D.scene.people.length) : 1;
// the people stand past the last plinth, never in front of a face with a number on it
const people = [[96, 2], [106, 10], [98, 20]].slice(0, n).flatMap(([x, y], i) =>
  person(`p-${i}`, () => ({ x, y, z: 2, k: 1.35, color: i === 0 ? ACC : "#8a817a", tone: i === 0 ? "hi" : "base", opacity: 1 })));

export default feedStory({
  name: "layout-plinth", D, accent: ACC,
  bodies: [plate, ...plinths, ...people],
  bounds: [[-93, -27, 0], [113, 39, 0], [-93, 39, 0], [113, -27, 0], [96, 16, 34], ...XS.map((x, i) => [x - PW / 2, -PD / 2, 2 + PH[i]])],
  band: { top: 0.38, bottom: 0.73, width: 0.94 },
  overlay: (P, view) => {
    let s = "";
    D.tiles.slice(0, 3).forEach((tile, i) => {
      // number and label printed on the plinth's front face, like a cut nameplate
      const face = faceMatrix(P, [XS[i] - PW / 2, PD / 2 + 0.05, 2 + PH[i]]);
      const lines = tile.label.split(" · ");
      const size = tile.value.length > 6 ? 10.5 : 13;
      s += `<g transform="${face}">` +
        txt(4, 6 + size, tile.value, { size, weight: 800, head: true, ls: -0.3, fill: tile.tone === "accent" ? ACC : SECTORS.ink }) +
        lines.map((l, k) => txt(4.4, 6 + size + 7 + k * 5.4, l, { size: 4.3, weight: 700, fill: SECTORS.muted, ls: 0.3 })).join("") +
        `</g>`;
    });
    const x = 16, y = view.h * 0.75, w = view.w - 32, h = view.h * 0.185;
    return s + rect(x, y, w, h, { fill: CARD, stroke: CARD_LINE, r: 8 }) +
      txt(x + 12, y + 13, D.chart.title.toUpperCase(), { size: 6.8, weight: 650, fill: SUBTLE, ls: 0.6 }) +
      chartOf(D.chart, x + 12, y + 20, w - 24, h - 34, ACC) + footer(view, D);
  },
});
