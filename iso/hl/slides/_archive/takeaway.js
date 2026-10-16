// Last slide: the short version. Three facts (a light numeral, a plain sentence), a question to the
// reader in the accent, and the CTA. DATA.slide: { title, facts: [{ value, text, accent? }], question, cta }.
const D = DATA, S = D.slide;
setAccent(D.direction);
frame(D);

let y = para(svg, M, 74, S.title, "title");
y += 26;
for (const f of S.facts) {
  mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);
  // long values ("Rp 520.1 B") step down a size so they never reach the sentence beside them
  type(svg, M - 1, y + 34, f.value, "num", { size: f.value.length > 8 ? 21 : 28, weight: 260, fill: f.accent ? "var(--acc)" : TONE.hi });
  para(svg, 150, y + 20, f.text, "body", { maxW: W - 150 - M, lh: 1.35, fill: "#d6d3d1" });
  y += 56;
}
mk("line", { x1: M, y1: y, x2: W - M, y2: y, class: "lo thin" }, svg);

// the question: what the comments are for
para(svg, M, y + 34, S.question, "title", { fill: TONE.hi, maxW: W - 2 * M });
type(svg, M, H - 48, S.cta, "label", { fill: "var(--acc)", size: 8.5, weight: 650 });
type(svg, W - M, H - 48, "Not financial advice.", "label", { fill: TONE.faint, size: 6.6, anchor: "end" });
