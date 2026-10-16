// Bars slide: every trade as a full-bleed bar in date order, true to scale. The outsized one carries a big
// label; the ordinary ones get one bracket with their usual size. A small bundle stack sits by the title.
const D = DATA, S1 = D.slide, ACC = accentOf(D);
const IT = S1.items, N = IT.length, MAX = Math.max(...IT.map((i) => i.value));
const X0 = PAD, X1 = VIEW.w - PAD, TOP = 182, BASE = 382, GAP = Math.min(4, ((X1 - X0) / N) * 0.25), BW = (X1 - X0 - GAP * (N - 1)) / N;
const xOf = (i) => X0 + i * (BW + GAP);
const hOf = (v) => Math.max(2.5, (v / MAX) * (BASE - TOP));
const icon = [plateOf("ip", 30, 22), stackOf("i1", -6, 0, 3, false), stackOf("i2", 6, 2, 16, true)];

export default carouselStory({
  D, accent: ACC, bodies: icon, bounds: [...plateBounds(30, 22), [6, 2, 20]], band: { top: 0.1, bottom: 0.24, width: 0.2, cx: 0.84 },
  overlay: (P, view) => {
    let s = textBlock(S1.title, PAD, 58, { size: 24, maxW: view.w * 0.66, accent: ACC, accentWords: S1.accentWords ?? [] }).svg;
    s += txt(PAD, 128, S1.sub, { size: 8.5, fill: SECTORS.muted });
    s += `<line x1="${X0}" y1="${BASE}" x2="${X1}" y2="${BASE}" stroke="#44403c" stroke-width="0.8"/>`;
    IT.forEach((it, i) => { s += rect(xOf(i), BASE - hOf(it.value), BW, hOf(it.value), { fill: it.hi ? ACC : "#57534e", r: Math.min(2, BW / 3) }); });
    const hi = IT.findIndex((i) => i.hi);
    const hx = xOf(hi) + BW / 2, right = hi > N * 0.6;
    s += txt(right ? xOf(hi) + BW : xOf(hi), TOP - 18, S1.hiLabel, { size: 22, weight: 800, head: true, anchor: right ? "end" : "start", fill: ACC, ls: -0.6 });
    s += txt(right ? xOf(hi) + BW : xOf(hi), TOP - 6, S1.hiNote, { size: 8, weight: 600, anchor: right ? "end" : "start", fill: SECTORS.muted });
    // the bracket over the ordinary trades
    const small = IT.map((it, i) => i).filter((i) => !IT[i].hi && IT[i].value < MAX * 0.2);
    if (small.length > 2 && S1.usualLabel) {
      const a = xOf(small[0]), b = xOf(small.at(-1)) + BW, by = BASE - 30;
      s += `<path d="M${a} ${by + 6}V${by}H${b}V${by + 6}" fill="none" stroke="${SECTORS.muted}" stroke-width="0.8"/>`;
      s += txt((a + b) / 2, by - 6, S1.usualLabel, { size: 9.5, weight: 700, anchor: "middle", fill: SECTORS.ink });
    }
    s += txt(X0, BASE + 12, S1.from, { size: 7.4, fill: SUBTLE }) + txt(X1, BASE + 12, S1.to, { size: 7.4, fill: SUBTLE, anchor: "end" });
    return s + chrome(view, D, ACC);
  },
});
