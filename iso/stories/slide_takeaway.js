// Last slide: the short version in three facts (big number left, plain words right), a caveat line when
// the data has one, and the CTA. The company tower stands bottom-right as the closing object.
const D = DATA, S1 = D.slide, ACC = accentOf(D);
const tower = companyTower("co", { x: 0, y: 0 }, { h: 46, w: 24, d: 20 });

export default carouselStory({
  D, accent: ACC, bodies: [plateOf("p", 44, 38), ...tower.bodies], bounds: [...plateBounds(44, 38), tower.top],
  band: { top: 0.6, bottom: 0.87, width: 0.3, cx: 0.8 },
  overlay: (P, view) => {
    let s = textBlock(S1.title, PAD, 58, { size: 24, accent: ACC, accentWords: S1.accentWords ?? [] }).svg;
    let y = 112;
    for (const f of S1.facts) {
      s += `<line x1="${PAD}" y1="${y}" x2="${view.w - PAD}" y2="${y}" stroke="#2f2a27" stroke-width="0.8"/>`;
      s += txt(PAD, y + 30, f.value, { size: 24, weight: 800, head: true, ls: -0.6, fill: f.tone === "accent" ? ACC : SECTORS.ink });
      s += textBlock(f.text, 140, y + 14, { size: 9.5, weight: 500, head: false, maxW: view.w - 140 - PAD, fill: "#d6d3d1", ls: 0, lh: 1.3 }).svg;
      y += 50;
    }
    s += `<line x1="${PAD}" y1="${y}" x2="${view.w - PAD}" y2="${y}" stroke="#2f2a27" stroke-width="0.8"/>`;
    if (S1.caveat) s += textBlock(S1.caveat, PAD, y + 10, { size: 7.4, weight: 500, head: false, maxW: view.w * 0.55, fill: SUBTLE, ls: 0, lh: 1.35 }).svg;
    // CTA
    const cy = view.h - 84;
    s += rect(PAD, cy, 170, 34, { fill: ACC, r: 17 });
    s += txt(PAD + 85, cy + 21.5, S1.cta, { size: 9.5, weight: 750, anchor: "middle", fill: "#140f0d" });
    return tower.signAt(P, D.symbol, ACC) + s + chrome(view, D, ACC);
  },
});
