// Weekly calendar, last slide: the week as five columns of dots (one dot per event, busiest day in the accent),
// then the question, a save prompt and the CTA.
// DATA.slide: { question, save, cta, days: [{ day, dow, groups: [{ items }] }] }
const D = DATA, S = D.slide;
setAccent(D.direction);
const counts = S.days.map((d) => d.groups.reduce((s, g) => s + g.items.length, 0));
const busiest = counts.indexOf(Math.max(...counts));
dotField(0, 0, W, H, { fx: W / 2, fy: 200, reach: 260, op: 0.36 });
watermark(W + 8, 250, String(S.days[busiest].day), 200, { anchor: "end", op: 0.05 });
glow(M + ((W - 2 * M) / S.days.length) * (busiest + 0.5), 190, 60, 60, 0.22);
frame(D);
const cw = (W - 2 * M) / S.days.length, BASE = 220;
type(svg, M, 74, "BUSIEST DAY", "caps", { fill: TONE.faint, size: 5.6 });
type(svg, M, 96, `${S.days[busiest].dow[0]}${S.days[busiest].dow.slice(1).toLowerCase()} ${S.days[busiest].day}, ${counts[busiest]} events`, "title", { fill: TONE.hi });
S.days.forEach((d, i) => {
  const cx = M + cw * (i + 0.5), hot = i === busiest;
  for (let k = 0; k < counts[i]; k++) {
    const col = k % 3, row = Math.floor(k / 3);
    mk("circle", { cx: cx + (col - 1) * 8, cy: BASE - 6 - row * 8, r: 2.6, style: hot ? "fill:var(--acc)" : `fill:${TONE.edge};fill-opacity:.7` }, svg);
  }
  type(svg, cx, BASE + 14, d.dow, "caps", { fill: hot ? "var(--acc)" : TONE.faint, size: 5.6, anchor: "middle" });
  type(svg, cx, BASE + 30, String(d.day), "num", { size: 14, weight: 300, fill: hot ? "var(--acc)" : TONE.hi, anchor: "middle" });
});
mk("line", { x1: M, y1: BASE + 2, x2: W - M, y2: BASE + 2, class: "lo thin" }, svg);

para(svg, M, 300, S.question, "title", { fill: TONE.hi, maxW: W - 2 * M });
type(svg, M, 350, S.save, "label", { fill: TONE.muted, size: 8 });
type(svg, M, H - 46, S.cta, "label", { fill: "var(--acc)", size: 8.5, weight: 650 });
type(svg, W - M, H - 46, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
grain();
