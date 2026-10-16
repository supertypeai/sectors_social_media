// Ranked slide (after Voronoi's CEO chart): full-bleed bars from the left edge, true to scale, an iso bust
// standing at each bar's end, the name and value set large beside it.
const D = DATA, S1 = D.slide, ACC = accentOf(D);
const CAM = { S: 1.5, dx: 0, dy: 0 };
const ROWS = S1.rows.slice(0, 5), TOP = 128, BOTTOM = 398, RH = (BOTTOM - TOP) / ROWS.length;
const MAX = Math.max(...ROWS.map((r) => r.value)), FULL = VIEW.w - 70;
const lenOf = (v) => Math.max(16, (v / MAX) * FULL); // a stub long enough to stand a bust on
const UN = unprojector(CAM);
// each bust stands on its bar's end, its base at the bar's lower edge
const busts = ROWS.flatMap((r, i) => {
  const L = lenOf(r.value), cy = TOP + RH * i + RH / 2;
  const [x, y] = UN(L + 1, cy + RH * 0.3, 0);
  return bust(`b-${i}`, () => ({ x, y, z: 0, k: 1.5, color: i === 0 ? ACC : "#8a817a", tone: i === 0 ? "hi" : "base" }));
});

export default carouselStory({
  D, accent: ACC, bodies: busts, cam: CAM,
  overlay: (P, view) => {
    let s = textBlock(S1.title, PAD, 58, { size: 24, accent: ACC, accentWords: S1.accentWords ?? [] }).svg;
    s += txt(PAD, 58 + 24 * 1.25 + 8, S1.sub, { size: 8.5, fill: SECTORS.muted });
    ROWS.forEach((r, i) => {
      const L = lenOf(r.value), y = TOP + RH * i, bh = RH * 0.64, by = y + (RH - bh) / 2;
      s += rect(-4, by, L + 4, bh, { fill: i === 0 ? ACC : "#3a3532", r: 3 });
      // long bar: words inside it, right-aligned before the bust; short bar: words after the bust
      const inside = L > view.w * 0.55;
      const tx = inside ? L - 18 : L + 22, anchor = inside ? "end" : "start", ink = inside ? "#140f0d" : SECTORS.ink;
      s += txt(tx, by + bh * 0.44, r.label.toUpperCase(), { size: 9.2, weight: 800, head: true, anchor, fill: ink, ls: 0.2 });
      s += txt(tx, by + bh * 0.44 + 13, r.display, { size: 11.5, weight: 800, head: true, anchor, fill: inside ? ink : i === 0 ? ACC : SECTORS.ink });
    });
    return s + chrome(view, D, ACC);
  },
});
