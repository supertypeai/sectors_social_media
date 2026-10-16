// Carousel kit: every slide is one still story. Slide 1 hooks (one hero number + a title + a big iso scene);
// the slides after it explain (a ranking, a curve, a takeaway). Text and charts are a flat SVG overlay in
// view units (360 × 450 at 4:5); iso bodies give each slide its object. post.mjs pastes this after scenes.js.
// DATA carries the post (copy, symbol, logo) and DATA.slide the slide (its kind, page, pages, and payload).

const VIEW = { w: 360, h: 450 };
const PAD = 22;

/** A slide: no engine text at all, the overlay carries every word. */
function carouselStory({ D, accent, bodies = [], bounds, band, cam, overlay }) {
  const camOf = cam ? () => ({ focus: [0, 0, 0], ...cam }) : sceneFit(bounds, band);
  OVERLAY((view) => overlay(projector(camOf(view), view), view));
  return ISO.story({
    name: `slide-${D.slide.page}`, duration: 1, aspect: "4:5", backdrop: "grid", poster: 0.9,
    theme: { ...SECTORS_THEME, accent }, brand: { name: "Sectors", accent },
    bodies: bodies.length ? bodies : [body("none", () => ({ x: 0, y: 0, z: 0, w: 1, d: 1, h: 0.1, opacity: 0 }))],
    camera: (t, { view }) => camOf(view),
    texts: [],
  });
}

/** The inverse of projector on the plane at height z: the world point under a screen point. */
const unprojector = (cam, view = VIEW) => {
  const C0 = Math.min(view.w, view.h) / 360, S = cam.S * C0, c = Math.SQRT1_2, zf = Math.sqrt(0.75);
  const ox = view.w / 2 + (cam.dx ?? 0) * C0, oy = view.h / 2 + (cam.dy ?? 0) * C0;
  return (sx, sy, z = 0) => {
    const a = (sx - ox) / (S * c), b = ((sy - oy) / S + z * zf) / (0.5 * c);
    return [(a + b) / 2, (b - a) / 2];
  };
};

/** Greedy word wrap by an average glyph width; good enough for Inter at display sizes. */
function wrap(text, size, maxW, glyph = 0.5) {
  const per = Math.max(4, Math.floor(maxW / (size * glyph)));
  const lines = [];
  let line = "";
  for (const w of String(text).split(" ")) {
    if (line && (line + " " + w).length > per) { lines.push(line); line = w; } else line = line ? line + " " + w : w;
  }
  if (line) lines.push(line);
  return lines;
}
/** A wrapped block of text; returns { svg, h }. Words in `accentWords` are coloured. */
function textBlock(text, x, y, { size = 20, weight = 800, maxW = VIEW.w - PAD * 2, lh = 1.08, fill = SECTORS.ink, head = true, accent, accentWords = [], anchor = "start", glyph = 0.5, ls = -0.4 } = {}) {
  const lines = wrap(text, size, maxW, glyph);
  const svg = lines.map((l, i) => {
    const spans = l.split(" ").map((w) => accentWords.some((a) => w.replace(/[.,]/g, "") === a) ? `<tspan fill="${accent}">${esc(w)}</tspan>` : esc(w)).join(" ");
    return `<text x="${x}" y="${y + size * (0.82 + i * lh)}" ${head ? FONT_H : FONT_B} font-size="${size}" font-weight="${weight}" fill="${fill}" text-anchor="${anchor}" letter-spacing="${ls}">${spans}</text>`;
  }).join("");
  return { svg, h: size * (0.82 + (lines.length - 1) * lh) + size * 0.3 };
}

/** The frame every slide shares: logo chip + kicker on top, page dots, source and site at the bottom. */
function chrome(view, D, accent) {
  const { page, pages } = D.slide;
  let s = "";
  if (D.logo) s += `<clipPath id="lc"><rect x="${PAD}" y="${PAD}" width="22" height="22" rx="5"/></clipPath>` +
    rect(PAD, PAD, 22, 22, { fill: "#fafaf9", r: 5 }) + `<image href="${D.logo}" x="${PAD + 2}" y="${PAD + 2}" width="18" height="18" clip-path="url(#lc)" preserveAspectRatio="xMidYMid meet"/>`;
  const kx = D.logo ? PAD + 30 : PAD;
  s += txt(kx, PAD + 9.5, D.copy.kicker, { size: 7.4, weight: 700, fill: SECTORS.amber, ls: 1 });
  s += txt(kx, PAD + 19.5, D.copy.tag, { size: 7.4, weight: 500, fill: SECTORS.muted });
  // page dots, the current one a pill in accent
  const dw = 5, gap = 4, total = pages * dw + (pages - 1) * gap + 8;
  let dx = view.w / 2 - total / 2;
  for (let i = 1; i <= pages; i++) {
    const w = i === page ? dw + 8 : dw;
    s += rect(dx, view.h - 34, w, 5, { fill: i === page ? accent : "#44403c", r: 2.5 });
    dx += w + gap;
  }
  if (page < pages) s += txt(view.w - PAD, view.h - 29.5, page === 1 ? "Swipe  →" : "→", { size: 7.4, weight: 650, fill: SECTORS.muted, anchor: "end" });
  s += txt(PAD, view.h - 12, D.copy.source, { size: 6.2, fill: SUBTLE }) + txt(view.w - PAD, view.h - 12, "sectors.app", { size: 6.2, weight: 650, fill: SECTORS.muted, anchor: "end" });
  return s;
}

/** A smooth path through points (Catmull-Rom → cubic Bézier). */
function smooth(pts) {
  let d = `M${pts[0][0].toFixed(1)} ${pts[0][1].toFixed(1)}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[i - 1] ?? pts[i], p1 = pts[i], p2 = pts[i + 1], p3 = pts[i + 2] ?? p2;
    // control points clamped to the segment's own y range: a running total never dips or overshoots
    const lo = Math.min(p1[1], p2[1]), hi = Math.max(p1[1], p2[1]), cl = (v) => Math.min(hi, Math.max(lo, v));
    const c1 = [p1[0] + (p2[0] - p0[0]) / 6, cl(p1[1] + (p2[1] - p0[1]) / 6)], c2 = [p2[0] - (p3[0] - p1[0]) / 6, cl(p2[1] - (p3[1] - p1[1]) / 6)];
    d += `C${c1[0].toFixed(1)} ${c1[1].toFixed(1)} ${c2[0].toFixed(1)} ${c2[1].toFixed(1)} ${p2[0].toFixed(1)} ${p2[1].toFixed(1)}`;
  }
  return d;
}

/** A bust (torso + head) for the ranked slide: the person() figure from the waist up. */
function bust(id, poseFn) {
  const part = (name, f) => body(`${id}-${name}`, (t, c) => f(poseFn(t, c)));
  return [
    part("torso", (q) => ({ x: q.x, y: q.y, z: q.z, w: 8 * q.k, d: 5 * q.k, h: 6 * q.k, r: 2.4 * q.k, b: 0.6, layer: 2, color: q.color, tone: q.tone,
      marks: (top, P, p) => { const Y = fy(P, p); return L2(Y, 0, p.h - 0.4, 0, p.h * 0.2) + L2(Y, -1.6, p.h - 0.3, 0, p.h - 2.4) + L2(Y, 1.6, p.h - 0.3, 0, p.h - 2.4); } })),
    part("head", (q) => ({ x: q.x, y: q.y, z: q.z + 6 * q.k, w: 5.8 * q.k, d: 5.8 * q.k, h: 5.6 * q.k, r: 2.9 * q.k, b: 0.6, layer: 2, color: SKIN })),
    part("hair", (q) => ({ x: q.x - 0.3 * q.k, y: q.y - 0.3 * q.k, z: q.z + 10.2 * q.k, w: 6 * q.k, d: 6 * q.k, h: 1.8 * q.k, r: 2.9 * q.k, b: 0.4, layer: 2, color: "#2e2926" })),
  ];
}
