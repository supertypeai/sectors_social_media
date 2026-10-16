// Hook for BYAN, two layers: the company's flame mark large and faint behind everything (who), and the
// coal haul truck in front as the focal point (what it does). Text on top as in stake_split.
const D = DATA, S = D.slide;
setAccent(D.direction);

// 1 · the mark, behind: big, faint, its drop not in the accent (one accent per slide: the coal)
// the hairline flame, large and faint up-right beside the headline: a watermark (the real logo is in the header)
drawFlameMark(mk("g", { opacity: 0.2 }, svg), { S: 2.5, cx: 292, cy: 176, dropCls: "sil", floorOn: false });

frame(D);
typeRun(svg, M - 3, 118, [[S.hero.num, 82, 220], [S.hero.unit, 34, 250, TONE.muted]]);
const sentence = S.deal ? `of ${S.name} changed owner in one deal` : `of ${S.name} was ${S.verb} by ${S.holder}`;
let y = para(svg, M, 148, sentence, "title", { accent: [] });
type(svg, M, y + 17, S.deal ? `${S.seller} → ${S.holder}` : `Stake ${S.before.toFixed(2)}% → ${S.after.toFixed(2)}% · ${S.day}`, "body", { fill: TONE.muted });

// 2 · the focal object, in front
drawMineCart(svg, { S: 2.35, cx: 180, cy: 318 });
