// Slide 1, the hook: one hero number, a title that makes you swipe, and the iso scene big underneath.
const D = DATA, S1 = D.slide, ACC = accentOf(D), SC = sceneFor(D, ACC);

export default carouselStory({
  D, accent: ACC, bodies: SC.bodies, bounds: SC.bounds, band: { top: 0.56, bottom: 0.9, width: 0.86 },
  overlay: (P, view) => {
    const size = Math.min(100, (view.w - PAD * 2) / (S1.hero.length * 0.56));
    let y = 64;
    let s = `<text x="${PAD - 2}" y="${y + size * 0.8}" ${FONT_H} font-size="${size}" font-weight="800" fill="${ACC}" letter-spacing="${-size * 0.045}">${esc(S1.hero)}</text>`;
    y += size * 1.04;
    const title = textBlock(S1.title, PAD, y, { size: 21, accent: ACC, accentWords: S1.accentWords ?? [] });
    s += title.svg;
    y += title.h + 4;
    s += textBlock(S1.sub, PAD, y, { size: 9.5, weight: 500, head: false, fill: SECTORS.muted, ls: 0 }).svg;
    return SC.signs(P) + s + chrome(view, D, ACC);
  },
});
