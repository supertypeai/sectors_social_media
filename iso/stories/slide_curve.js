// Curve slide (after Lendermarket): one smooth line across the full width on a true time axis, a soft
// fill under it, and a few key points labelled large with a drop line each. Small iso accent by the title.
const D = DATA, S1 = D.slide, ACC = accentOf(D);
const PT = S1.points; // [{ date, y, label?, note? }] with label set on the key points
const T = PT.map((p) => Date.parse(p.date + "T00:00:00Z"));
const t0 = T[0], t1 = Math.max(T.at(-1), t0 + 864e5);
const Y = PT.map((p) => p.y), ylo = Math.min(...Y), yhi = Math.max(...Y), span = yhi - ylo || 1;
const TOP = 196, BASE = 388, X0 = 0, X1 = VIEW.w;
const sx = (t) => 30 + ((t - t0) / (t1 - t0)) * (X1 - 70);
const sy = (v) => BASE - 22 - ((v - ylo) / span) * (BASE - 22 - TOP);
const icon = S1.icon === "tower" ? companyTower("ic", { x: 0, y: 0 }, { h: 30, w: 16, d: 14 }) : null;
const iconBodies = icon ? [plateOf("ip", 30, 26), ...icon.bodies] : [plateOf("ip", 30, 22), stackOf("i1", -6, 0, 6, false), stackOf("i2", 6, 2, 14, true)];

export default carouselStory({
  D, accent: ACC, bodies: iconBodies, bounds: [...plateBounds(30, 26), icon ? icon.top : [6, 2, 18]], band: { top: 0.1, bottom: 0.25, width: 0.2, cx: 0.84 },
  overlay: (P, view) => {
    let s = `<defs><linearGradient id="fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0" stop-color="${ACC}" stop-opacity="0.32"/><stop offset="1" stop-color="${ACC}" stop-opacity="0"/></linearGradient></defs>`;
    s += textBlock(S1.title, PAD, 58, { size: 24, maxW: view.w * 0.66, accent: ACC, accentWords: S1.accentWords ?? [] }).svg;
    s += txt(PAD, 128, S1.sub, { size: 8.5, fill: SECTORS.muted });
    const pts = PT.map((p, i) => [sx(T[i]), sy(p.y)]);
    const line = smooth([[X0, pts[0][1]], ...pts, [X1, pts.at(-1)[1]]]);
    s += `<path d="${line}L${X1} ${BASE}L${X0} ${BASE}Z" fill="url(#fill)"/>`;
    s += `<path d="${line}" fill="none" stroke="${ACC}" stroke-width="2.2" stroke-linecap="round"/>`;
    PT.forEach((p, i) => {
      if (!p.label) return;
      const [x, y] = pts[i];
      // a label crowded by the next labelled point steps to the left of its dot, level with it
      const next = PT.findIndex((q, k) => k > i && q.label);
      const crowded = next > 0 && pts[next][0] - x < 130; // two 19-unit labels need about this much room side by side
      const anchor = crowded || x > view.w * 0.75 ? "end" : x < view.w * 0.25 ? "start" : "middle";
      const ax = anchor === "end" ? x - 10 : anchor === "start" ? x + 10 : x; // clear of the drop line
      const ly = crowded ? y + 34 : y - 22; // crowded: below and left, in the empty space beside the rise
      s += `<line x1="${x}" y1="${y}" x2="${x}" y2="${BASE}" stroke="${ACC}" stroke-opacity="0.45" stroke-width="0.8"/>`;
      s += `<circle cx="${x}" cy="${y}" r="5" fill="#fafaf9" stroke="${ACC}" stroke-width="2.4"/>`;
      s += txt(ax, ly, p.label, { size: 19, weight: 800, head: true, anchor, ls: -0.5 });
      if (p.note) s += txt(ax, ly + 12, p.note, { size: 7.6, weight: 600, anchor, fill: SECTORS.muted });
    });
    return s + chrome(view, D, ACC);
  },
});
