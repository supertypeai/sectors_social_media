// News compilation, direction 4: the day in numbers. Each story reduced to its one number, set big, with the
// logo, ticker and a one-line "what" under it. A 2-column board; the lead takes the full first row.
const D = DATA, S = D.stories.filter((s) => s.key).slice(0, 5);
setAccent("buy");
const GI = "#b2d2b9", TI = "#dc8d74";
dotField(0, 0, W, H, { fx: W * 0.5, fy: 320, reach: 320, op: 0.28 });

const y0 = SAFE.top + 8;
mk("circle", { cx: M + 2.5, cy: y0 - 2.6, r: 2.5, class: "accf" }, svg);
type(svg, M + 10, y0, "IDX NEWS", "caps", { fill: TONE.hi, weight: 750 });
type(svg, W - M, y0, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
type(svg, M, y0 + 46, "Today in", "hero", { size: 36, weight: 500 });
type(svg, M, y0 + 84, "numbers", "hero", { size: 36, weight: 500, fill: GI });

function cell(s, x, y, w, h, big) {
  const ink = s.bear ? TI : GI;
  mk("rect", { x, y, width: w, height: h, rx: 10, style: `fill:${TONE.card};fill-opacity:.7;stroke:${TONE.mid};stroke-width:.8px` }, svg);
  logoChip(svg, x + 18, y + 20, 10, s.logo, s.sym);
  typeRun(svg, x + 33, y + 23.5, [[s.sym, 9.5, 750, TONE.hi], [`  ${s.cat.toUpperCase()}`, 5.8, 700, ink]]);
  type(svg, x + 12, y + (big ? 76 : 66), s.key.value, "num", { size: big ? 44 : s.key.value.length > 9 ? 22 : 28, weight: 500, fill: ink });
  type(svg, x + 12, y + (big ? 90 : 79), s.key.label, "label", { fill: TONE.muted, size: 7.4 });
  const lines = wrapText(s.headline, 7.8, w - 24).slice(0, big ? 1 : 2);
  lines.forEach((l, i) => type(svg, x + 12, y + h - (lines.length - i) * 10 - 4, l, "label", { fill: "#d9d5cc", size: 7.8 }));
}
const top = y0 + 104, G = 8, Wd = W - 2 * M, hBig = 124, rest = S.slice(1), rowsN = Math.ceil(rest.length / 2);
const hS = (SAFE.bottom - 30 - top - hBig - G * rowsN) / rowsN, wS = (Wd - G) / 2;
cell(S[0], M, top, Wd, hBig, true);
rest.forEach((s, i) => cell(s, M + (i % 2) * (wS + G), top + hBig + G + Math.floor(i / 2) * (hS + G), wS, hS, false));

type(svg, M, SAFE.bottom - 4, "Read every story on sectors.app/indonesia/news", "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
