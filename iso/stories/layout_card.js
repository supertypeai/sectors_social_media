// Layout A, "scene + card": the iso vignette says who and what; a flat card underneath carries the
// chart and three stat tiles, so every number reads like a normal chart.
const D = DATA, ACC = accentOf(D), SC = sceneFor(D, ACC);

export default feedStory({
  name: "layout-card", D, accent: ACC,
  bodies: SC.bodies, bounds: SC.bounds, band: { top: 0.38, bottom: 0.585, width: 0.8 },
  overlay: (P, view) => {
    const x = 16, y = view.h * 0.595, w = view.w - 32, h = view.h * 0.355;
    return SC.signs(P) +
      rect(x, y, w, h, { fill: CARD, stroke: CARD_LINE, r: 8 }) +
      txt(x + 12, y + 15, D.chart.title.toUpperCase(), { size: 6.8, weight: 650, fill: SUBTLE, ls: 0.6 }) +
      chartOf(D.chart, x + 12, y + 24, w - 24, h * 0.4, ACC) +
      tiles(D.tiles, x + 12, y + h * 0.66, w - 24, h * 0.28, ACC) +
      footer(view, D);
  },
});
