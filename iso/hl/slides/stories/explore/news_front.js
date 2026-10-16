// News compilation, direction 2: front page. The lead story's photo across the top with its ticker, headline
// and number on the fade; the other stories below as compact rows with logos.
const D = DATA, S = D.stories.slice(0, 5), L = S[0];
setAccent(L.bear ? "sell" : "buy");
const GI = "#b2d2b9", TI = "#dc8d74";
photo(L.photo, 0, 0, W, 330, { fade: 0.55 });

const y0 = SAFE.top + 8;
const cap = (x, text, anchor = "start") => {
  const t = type(svg, x, y0, text, "caps", { fill: TONE.hi, weight: 750, anchor }), b = t.getBBox();
  svg.insertBefore(mk("rect", { x: b.x - 8, y: y0 - 9.5, width: b.width + 16, height: 15, rx: 7.5, style: `fill:${TONE.ground};fill-opacity:.8;stroke:${TONE.mid};stroke-width:.6px` }), t);
};
cap(M + 2, "TODAY ON THE IDX");
cap(W - M, D.company, "end");

// the lead on the photo's foot
logoPill(svg, M, 196, L.sym, L.logo);
type(svg, M + L.sym.length * 7.4 + 44, 211, L.cat.toUpperCase(), "caps", { fill: "var(--acc)", size: 6 });
let y = para(svg, M, 244, L.headline, "title", { maxW: W - 2 * M });
if (L.key) typeRun(svg, M, y + 34, [[L.key.value, 30, 500, L.bear ? TI : GI], [`  ${L.key.label}`, 8, 500, TONE.muted]]);

// the rest
const TOP = Math.max(y + 56, 330), rows = S.slice(1), RH = (SAFE.bottom - 30 - TOP) / rows.length;
type(svg, M, TOP - 4, "ALSO TODAY", "caps", { fill: TONE.faint, size: 5.6 });
rows.forEach((s, i) => {
  const ry = TOP + 8 + i * RH, ink = s.bear ? TI : GI;
  mk("line", { x1: M, y1: ry, x2: W - M, y2: ry, class: "lo thin" }, svg);
  logoChip(svg, M + 12, ry + RH / 2, 12, s.logo, s.sym);
  typeRun(svg, M + 32, ry + RH / 2 - 6, [[s.sym, 9.5, 750, TONE.hi], [`  ${s.cat.toUpperCase()}`, 6, 700, ink]]);
  const h = wrapText(s.headline, 8.6, W - 2 * M - 32)[0];
  type(svg, M + 32, ry + RH / 2 + 8, h === s.headline ? h : s.headline.split(" ").slice(0, Math.max(3, h.split(" ").length - 1)).join(" "), "label", { fill: "#d9d5cc", size: 8.6 });
});

type(svg, M, SAFE.bottom - 4, "Read every story on sectors.app/indonesia/news", "label", { fill: TONE.hi, size: 9, weight: 600 });
grain(0.09);
