// Sectors Hairline: our own style on the Hairline kernel (iso/vendor/kernel.js, MIT, Lucas Markes).
// The kernel gives the geometry (rounded rings, prisms, projection, reflections); this file gives the look.
//
//   - Five warm tones, never colour fills: plates are filled with the ground, so a solid is its outline.
//   - One accent (teal for buying, rose for selling), allowed on ONE thing per slide: a stroke and its dots.
//   - Bright outside, dim inside: silhouette in `edge`, the crease one step dimmer, guides dashed in `lo`.
//   - Type is editorial: huge light numerals, small tracked capitals, tabular figures.
//
// Slides draw into a 360 × 450 viewBox (4:5) rendered at 1080 × 1350. render.mjs pastes, in order:
// the kernel, this file, DATA, the slide.
const { Cam, fit, proj, facing, rings, rrect, circ, prism, ringAt, run, hull, poly, open, seg, mk, solid, put, ghost } = HL;

// A feed post is 360 × 450 (4:5); a story is 360 × 640 (9:16). render.mjs sets FORMAT from DATA.format.
const W = 360, H = typeof FORMAT !== "undefined" && FORMAT === "story" ? 640 : 450, M = 24; // the slide and its margin
// Colours are Supertype Foundations' dark theme (github.com/supertypeai/foundations, src/theme.css .dark):
// ground = --espresso-background, card = --card, lo = --muted, mid = --border, hi = --foreground,
// muted = --subtle-foreground; buy = --chart-1 (the brand green), sell = --chart-2 (terracotta).
const TONE = { ground: "#141210", card: "#272421", lo: "#322e2a", mid: "#48423d", edge: "#8a827b", hi: "#efece7", muted: "#a19b8c", faint: "#6b645e" };
// fig = the Sectors maroon (#9D0142) for news and calendar posts: lifted to #d0326f so it reads as type on the
// dark ground; the raw #9D0142 is the page's corner glow (setAccent below)
const ACCENTS = { buy: "#81a789", sell: "#c07159", info: "#74a3be", warn: "#c59920", fig: "#d0326f" };

// ---------------------------------------------------------------- the page
const SVGNS = "http://www.w3.org/2000/svg";
const svg = document.querySelector("svg#slide");
const STYLE = `
  body{margin:0;background:${TONE.ground}}
  svg#slide{display:block;background:radial-gradient(120% 90% at 70% 60%, #1e1b18 0%, ${TONE.ground} 62%)}
  #slide path,#slide polygon,#slide ellipse,#slide line,#slide circle.p{fill:${TONE.ground};stroke:${TONE.mid};stroke-width:1.5px;vector-effect:non-scaling-stroke;stroke-linejoin:round;stroke-linecap:round}
  #slide .nf{fill:none} #slide .fo{stroke:none}
  #slide .sil{stroke:${TONE.edge}} #slide .lo{stroke:${TONE.lo}} #slide .hi{stroke:${TONE.hi}}
  #slide .acc{stroke:var(--acc)} #slide .accf{fill:var(--acc);stroke:none}
  #slide .dash{stroke-dasharray:1.5 4;stroke:${TONE.faint}}
  #slide .thin{stroke-width:1px}
  #slide .ghost path{fill:none;stroke:${TONE.mid}}
  #slide text{font-family:"Inter Tight",Inter,sans-serif;font-feature-settings:"tnum" 1,"ss01" 1;fill:${TONE.hi};stroke:none}
`;
document.head.insertAdjacentHTML("beforeend", `<style>${STYLE}</style>`);
const setAccent = (dir) => {
  svg.style.setProperty("--acc", ACCENTS[dir] ?? ACCENTS.buy);
  // the maroon posts (news, calendar) sit on the Sectors page: near-black with a maroon glow rising from the
  // bottom-left corner
  if (dir === "fig" || DATA.page === "maroon") {
    svg.style.background = `radial-gradient(70% 45% at 0% 100%, rgba(157,1,66,.2) 0%, rgba(157,1,66,.06) 45%, rgba(157,1,66,0) 75%), ${TONE.ground}`;
  }
};

// ---------------------------------------------------------------- type
const esc = (s) => String(s).replace(/&/g, "&amp;").replace(/</g, "&lt;");
/** One line of type. role: "hero" | "title" | "body" | "label" | "caps" | "num". */
const ROLES = {
  hero: { size: 96, weight: 250, ls: -0.05 },
  title: { size: 21, weight: 560, ls: -0.022 },
  body: { size: 9.2, weight: 430, ls: 0 },
  label: { size: 8, weight: 500, ls: 0 },
  caps: { size: 6.6, weight: 600, ls: 0.16 },
  num: { size: 26, weight: 300, ls: -0.03 },
};
function type(parent, x, y, text, role = "body", { fill, anchor = "start", size, weight, cls } = {}) {
  const r = ROLES[role], s = size ?? r.size;
  const t = mk("text", { x, y, "font-size": s, "font-weight": weight ?? r.weight, "letter-spacing": `${(r.ls * s).toFixed(2)}`, "text-anchor": anchor, ...(cls ? { class: cls } : {}) }, parent);
  if (fill) t.style.fill = fill; // style, not the attribute: the stylesheet's text rule outranks attributes
  t.innerHTML = role === "caps" ? esc(String(text).toUpperCase()) : esc(text);
  return t;
}
/** Mixed sizes on one baseline, Lendermarket style: [[text, size, weight, fill?], …]. Returns the width used. */
function typeRun(parent, x, y, parts, { anchor = "start" } = {}) {
  const t = mk("text", { x, y, "text-anchor": anchor }, parent);
  for (const [s, size, weight, fill, dy] of parts) {
    const sp = mk("tspan", { "font-size": size, "font-weight": weight, "letter-spacing": `${(-0.04 * size).toFixed(2)}`, ...(fill ? { style: `fill:${fill}` } : {}), ...(dy ? { dy } : {}) }, t);
    sp.textContent = String(s).replace(/ /g, " "); // SVG collapses spaces between tspans; keep them
  }
  return t;
}
/** Greedy wrap by average glyph width (Inter Tight ≈ 0.5 em at display weights). */
function wrapText(text, size, maxW, em = 0.5) {
  const per = Math.max(4, Math.floor(maxW / (size * em))), out = [];
  let line = "";
  for (const w of String(text).split(" ")) {
    if (line && (line + " " + w).length > per) { out.push(line); line = w; } else line = line ? `${line} ${w}` : w;
  }
  return line ? [...out, line] : out;
}
/** Steps a text's size down (in half points, never below `min`) until it wraps into at most `lines` lines at
 *  `maxW`. Returns { size, lines }. Never cuts words: if it still runs long at `min`, every line is returned. */
function fitText(text, { size, min = size * 0.7, maxW = W - 2 * M, lines = 3, em = 0.5 } = {}) {
  let s = size, out = wrapText(text, s, maxW, em);
  while (out.length > lines && s - 0.5 >= min) { s -= 0.5; out = wrapText(text, s, maxW, em); }
  return { size: s, lines: out };
}
/** A wrapped paragraph; returns the y under its last line. `accent` words are set in the accent colour. */
function para(parent, x, y, text, role = "title", { maxW = W - 2 * M, lh = 1.12, accent = [], fill } = {}) {
  const r = ROLES[role], lines = wrapText(text, r.size, maxW);
  lines.forEach((l, i) => {
    const t = type(parent, x, y + i * r.size * lh, "", role, { fill });
    t.innerHTML = l.split(" ").map((w) => accent.includes(w.replace(/[.,]/g, "")) ? `<tspan style="fill:var(--acc)">${esc(w)}</tspan>` : esc(w)).join(" ");
  });
  return y + (lines.length - 1) * r.size * lh;
}

// ---------------------------------------------------------------- photo
/** A photo filling a box, toned down to sit on the warm ground, fading into it at the bottom. */
let photoId = 0;
function photo(href, x, y, w, h, { fade = 0.55, dim = 0.78 } = {}) {
  if (!href) return null;
  const id = `ph${++photoId}`, defs = mk("defs", {}, svg);
  mk("rect", { x, y, width: w, height: h }, mk("clipPath", { id: `${id}c` }, defs));
  // the photo itself fades out through a mask, so it melts into whatever is behind it (no hard edge, whatever
  // the page's background gradient does there); the overlay only darkens the top for the header
  const mg = mk("linearGradient", { id: `${id}m`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  // an eased fade (smoothstep, many stops) over the lower `fade` of the photo: no visible start or end
  mk("stop", { offset: 0, "stop-color": "#fff", "stop-opacity": 1 }, mg);
  for (let i = 0; i <= 12; i++) {
    const t = i / 12, o = 1 - t * t * (3 - 2 * t);
    mk("stop", { offset: (1 - fade + fade * t).toFixed(3), "stop-color": "#fff", "stop-opacity": (o * o).toFixed(3) }, mg);
  }
  const mask = mk("mask", { id: `${id}k`, maskUnits: "userSpaceOnUse", x, y, width: w, height: h }, defs);
  mk("rect", { x, y, width: w, height: h, style: `fill:url(#${id}m);stroke:none` }, mask);
  const g = mk("g", { "clip-path": `url(#${id}c)`, mask: `url(#${id}k)` }, svg);
  mk("image", { href, x, y, width: w, height: h, preserveAspectRatio: "xMidYMid slice", style: `filter:saturate(.7) brightness(${dim}) contrast(1.05)` }, g);
  const tg = mk("linearGradient", { id: `${id}t`, x1: 0, y1: 0, x2: 0, y2: 1 }, defs);
  mk("stop", { offset: 0, "stop-color": TONE.ground, "stop-opacity": 0.55 }, tg);
  mk("stop", { offset: 0.35, "stop-color": TONE.ground, "stop-opacity": 0.12 }, tg);
  mk("stop", { offset: 1, "stop-color": TONE.ground, "stop-opacity": 0.3 }, tg);
  mk("rect", { x, y, width: w, height: h, style: `fill:url(#${id}t);stroke:none` }, g);
  return g;
}

/** A round logo chip (white disc, the logo inside) centred at (cx, cy). */
let chipId = 0;
function logoChip(parent, cx, cy, r, href, sym = "") {
  if (!href) { // no logo file: the ticker's first letter in a hairline disc, so rows still line up
    mk("circle", { cx, cy, r, class: "nf", style: `stroke:${TONE.edge};stroke-width:.8px` }, parent);
    type(parent, cx, cy + r * 0.38, sym.slice(0, 1), "label", { fill: TONE.hi, size: r * 1.05, weight: 600, anchor: "middle" });
    return;
  }
  const id = `lc${++chipId}`;
  mk("circle", { cx, cy, r: r - 0.6 }, mk("clipPath", { id }, mk("defs", {}, parent)));
  mk("circle", { cx, cy, r, style: `fill:#f2efe9;stroke:${TONE.mid};stroke-width:.8px` }, parent);
  const p = r * 0.78;
  mk("image", { href, x: cx - p, y: cy - p, width: 2 * p, height: 2 * p, "clip-path": `url(#${id})`, preserveAspectRatio: "xMidYMid meet" }, parent);
}
/** A ticker pill in the accent with the company's logo at its left; returns its width. */
function logoPill(parent, x, y, sym, logo, { h = 22, size = 12 } = {}) {
  // solid accent pill, white ticker; the logo (or the ticker's first letter on a white disc) at the left
  const w = sym.length * size * 0.66 + h + 16; // room on both sides of the ticker
  mk("rect", { x, y, width: w, height: h, rx: h / 2, style: "fill:var(--acc);stroke:none" }, parent);
  const r = h / 2 - 3.5, cx = x + h / 2 + 2, cy = y + h / 2;
  if (logo) logoChip(parent, cx, cy, r, logo);
  else {
    mk("circle", { cx, cy, r, style: "fill:#ffffff;stroke:none" }, parent);
    type(parent, cx, cy + r * 0.4, sym.slice(0, 1), "label", { fill: "var(--acc)", size: r * 1.15, weight: 800, anchor: "middle" });
  }
  type(parent, x + h + 5, y + h / 2 + size * 0.36, sym, "label", { fill: "#ffffff", size, weight: 750 });
  return w;
}

// ---------------------------------------------------------------- texture and detail
/** Film grain over the whole slide: fine noise at very low opacity, so flat areas stop looking digital. */
function grain(opacity = 0.07) {
  const f = mk("filter", { id: "grain", x: 0, y: 0, width: "100%", height: "100%" }, mk("defs", {}, svg));
  mk("feTurbulence", { type: "fractalNoise", baseFrequency: 1.1, numOctaves: 2, stitchTiles: "stitch" }, f);
  mk("feColorMatrix", { type: "saturate", values: 0 }, f);
  mk("rect", { x: 0, y: 0, width: W, height: H, filter: "url(#grain)", style: `opacity:${opacity};mix-blend-mode:overlay;pointer-events:none` }, svg);
}
/** A dot grid across a box that fades out from (fx, fy): the floor of the page. */
function dotField(x0, y0, x1, y1, { step = 9, fx = W * 0.7, fy = H * 0.2, reach = 260, op = 0.32 } = {}) {
  const g = mk("g", {}, svg);
  for (let x = x0; x <= x1; x += step) for (let y = y0; y <= y1; y += step) {
    const d = Math.hypot(x - fx, y - fy) / reach;
    if (d < 1) mk("circle", { cx: x, cy: y, r: 0.5, fill: TONE.edge, opacity: (op * (1 - d) ** 1.5).toFixed(3) }, g);
  }
  return g;
}
/** A soft accent glow (a blurred disc) behind something. */
function glow(cx, cy, rx, ry, op = 0.16) {
  // on the maroon pages the corner glow is already the page's light: in-slide glows go quiet so there's one
  if (DATA.page === "maroon" || DATA.direction === "fig") op *= 0.3;
  const id = `gl${Math.round(cx)}${Math.round(cy)}`, rg = mk("radialGradient", { id }, mk("defs", {}, svg));
  mk("stop", { offset: 0, "stop-color": "var(--acc)", "stop-opacity": op }, rg);
  mk("stop", { offset: 1, "stop-color": "var(--acc)", "stop-opacity": 0 }, rg);
  mk("ellipse", { cx, cy, rx, ry, style: `fill:url(#${id});stroke:none` }, svg);
}
/** Huge outlined letters, barely there: a watermark. */
function watermark(x, y, text, size, { anchor = "start", op = 0.07 } = {}) {
  const t = type(svg, x, y, text, "hero", { size, weight: 700, anchor });
  t.style.fill = "none";
  t.style.stroke = TONE.hi;
  t.style.strokeWidth = "0.6px";
  t.style.opacity = op;
  return t;
}
/** Small hairline glyphs, one per kind of event. (cx, cy) is the centre, s the size. */
function glyph(parent, kind, cx, cy, s = 4, color = TONE.muted) {
  const st = `fill:none;stroke:${color};stroke-width:.9px;stroke-linecap:round;stroke-linejoin:round`;
  const p = (d) => mk("path", { d, style: st }, parent);
  if (kind === "div") { // a coin
    mk("circle", { cx, cy, r: s, style: st }, parent); mk("circle", { cx, cy, r: s * 0.55, style: st }, parent);
  } else if (kind === "rights") { // a ticket
    p(`M${cx - s} ${cy - s * 0.7}H${cx + s}V${cy - s * 0.2}a${s * 0.2} ${s * 0.2} 0 0 0 0 ${s * 0.4}V${cy + s * 0.7}H${cx - s}V${cy + s * 0.2}a${s * 0.2} ${s * 0.2} 0 0 0 0 ${-s * 0.4}Z`);
  } else if (kind === "split") { // one block becoming two
    p(`M${cx - s} ${cy - s * 0.7}h${s * 0.8}v${s * 1.4}h${-s * 0.8}Z M${cx + s * 0.2} ${cy - s * 0.7}h${s * 0.8}v${s * 1.4}h${-s * 0.8}Z`);
  } else if (kind === "warrant") { // a key
    mk("circle", { cx: cx - s * 0.45, cy, r: s * 0.45, style: st }, parent); p(`M${cx} ${cy}H${cx + s}M${cx + s * 0.7} ${cy}v${s * 0.4}`);
  } else if (kind === "agm") { // three heads at a table
    for (const dx of [-s * 0.7, 0, s * 0.7]) mk("circle", { cx: cx + dx, cy: cy - s * 0.25, r: s * 0.26, style: st }, parent);
    p(`M${cx - s} ${cy + s * 0.55}H${cx + s}`);
  } else { // a bell, for IPO listings and anything else
    p(`M${cx - s * 0.7} ${cy + s * 0.4}Q${cx - s * 0.7} ${cy - s} ${cx} ${cy - s}Q${cx + s * 0.7} ${cy - s} ${cx + s * 0.7} ${cy + s * 0.4}Z`);
  }
}

/** A logo and the ticker beside it, baseline at y; returns the width used. */
function tickerChip(parent, x, y, sym, logo, { size = 8.4, fill = TONE.hi } = {}) {
  const r = size * 0.62;
  logoChip(parent, x + r, y - size * 0.34, r, logo, sym);
  type(parent, x + 2 * r + 3.5, y, sym, "label", { fill, size, weight: 700 });
  return 2 * r + 3.5 + sym.length * size * 0.66;
}

// ---------------------------------------------------------------- frame
/** The kicker (accent dot, tracked caps, company) and the footer (source, page marks, site). */
function frame(D) {
  const g = mk("g", {}, svg);
  const onPhoto = !!D.slide?.photo;
  mk("circle", { cx: M + 2.5, cy: M + 3.4, r: 2.5, class: "accf" }, g);
  const kick = type(g, M + 10, M + 6, D.kicker, "caps", { fill: TONE.hi, weight: 750 });
  // the company's real logo (logos/<SYM>.webp) as a small round chip at the right, its name beside it
  if (D.logo) {
    const r = 9, cx = W - M - r, cy = M + 3.6;
    const cp = mk("clipPath", { id: "logochip" }, mk("defs", {}, g));
    mk("circle", { cx, cy, r }, cp);
    mk("circle", { cx, cy, r: r + 0.6, style: `fill:#f2efe9;stroke:${TONE.mid}` }, g);
    mk("image", { href: D.logo, x: cx - r + 1.5, y: cy - r + 1.5, width: 2 * r - 3, height: 2 * r - 3, "clip-path": "url(#logochip)", preserveAspectRatio: "xMidYMid meet" }, g);
  }
  const co = type(g, W - M - (D.logo ? 24 : 0), M + 6, D.company, "caps", { fill: onPhoto ? TONE.hi : TONE.muted, weight: 700, anchor: "end" });
  if (onPhoto) {
    // over a photo: dark capsules measured to the real text, drawn behind it; no rule across the photo
    const cap = (x0, x1) => g.insertBefore(mk("rect", { x: x0 - 7, y: M - 4.5, width: x1 - x0 + 14, height: 16, rx: 8,
      style: `fill:${TONE.ground};fill-opacity:.85;stroke:${TONE.mid};stroke-width:.6px` }, g), g.firstChild);
    const kb = kick.getBBox(), cb = co.getBBox();
    cap(M, kb.x + kb.width);
    cap(cb.x, D.logo ? W - M : cb.x + cb.width);
  } else {
    mk("line", { x1: M, y1: M + 16, x2: W - M, y2: M + 16, class: "lo thin" }, g);
  }
  // footer: source left, slide marks centre, site right
  mk("line", { x1: M, y1: H - 32, x2: W - M, y2: H - 32, class: "lo thin" }, g);
  type(g, M, H - 19, D.source, "label", { fill: TONE.faint, size: 6.4 });
  type(g, W - M, H - 19, "sectors.app", "label", { fill: TONE.muted, size: 6.4, anchor: "end", weight: 600 });
  const { page, pages } = D.slide;
  for (let i = 1; i <= pages; i++) mk("line", { x1: W / 2 - pages * 7 + i * 14 - 5, y1: H - 21.5, x2: W / 2 - pages * 7 + i * 14 + 3, y2: H - 21.5, class: i === page ? "acc" : "lo" }, g);
  return g;
}

// ---------------------------------------------------------------- story frame (9:16)
// Instagram draws its own UI over a story: the progress bar and profile row (≈120 px of 1920 at the top) and
// the reply field (≈170 px at the bottom). SAFE keeps clear of both with a little air, so the story still uses
// the full height. Backgrounds, photos and texture may run full-bleed; words, numbers and logos stay inside SAFE.
const SAFE = { top: 56, bottom: 572, x0: M, x1: W - M };
/** The story's kicker (accent dot, tracked caps) and company/date at the top of the safe zone, and the source
 *  and sectors.app at its bottom. Returns { top, bottom }: the band left for the story's content. */
function storyFrame(D) {
  const g = mk("g", {}, svg), y = SAFE.top + 8;
  mk("circle", { cx: M + 2.5, cy: y - 2.6, r: 2.5, class: "accf" }, g);
  type(g, M + 10, y, D.kicker, "caps", { fill: TONE.hi, weight: 750 });
  if (D.company) type(g, W - M, y, D.company, "caps", { fill: TONE.muted, weight: 700, anchor: "end" });
  mk("line", { x1: M, y1: y + 10, x2: W - M, y2: y + 10, class: "lo thin" }, g);
  const by = SAFE.bottom - 6;
  mk("line", { x1: M, y1: by - 13, x2: W - M, y2: by - 13, class: "lo thin" }, g);
  if (D.source) type(g, M, by, D.source, "label", { fill: TONE.faint, size: 6.4 });
  type(g, W - M, by, "sectors.app", "label", { fill: TONE.muted, size: 6.8, anchor: "end", weight: 650 });
  return { top: y + 26, bottom: by - 24 };
}

// ---------------------------------------------------------------- solids (the kernel's construction)
/** A camera of scale S whose box of world points is centred on (cx, cy). */
function camera(S, pts, cx, cy) {
  const C = Cam(45, 0.5, S);
  fit(C, pts, cx, cy);
  return { C, P: proj(C), front: facing(C) };
}
/** A rounded solid from z0 to z1 on footprint ring: its silhouette and one crease. cls goes on the silhouette. */
function slab(parent, K, ring, inner, z0, z1, cls = "sil") {
  const el = solid(parent);
  put(el, prism(K.P, K.front, ring, inner, z0, z1));
  el.sil.setAttribute("class", cls);
  return el;
}
/** A round column's footprint and crease ring at (x, y), radius R. */
function disc(x, y, R, b = 1.6, n = 48) {
  const shift = (ring) => ring.map((q) => ({ ...q, u: q.u + x, v: q.v + y }));
  return [shift(circ(R, n)), shift(circ(R - b, n))];
}
/** A ring's front half at height z, as an open line (a seam round a column). */
const seam = (K, ring, z) => open(ringAt(K.P, run(ring, K.front), z));
/** A fading mirror under a solid, in our own frame (the kernel's fade is sized to 400 × 320). */
let fadeId = 0;
function mirror(parent, K, ring, z0, depth) {
  const r = ghost(K.P, K.front, ring, z0, depth), id = `fd${++fadeId}`;
  const defs = mk("defs", {}, svg);
  const lg = mk("linearGradient", { id: `${id}g`, gradientUnits: "userSpaceOnUse", x1: 0, y1: r.y0, x2: 0, y2: r.y1 }, defs);
  mk("stop", { offset: 0, "stop-color": "#fff", "stop-opacity": 0.55 }, lg);
  mk("stop", { offset: 1, "stop-color": "#fff", "stop-opacity": 0 }, lg);
  const m = mk("mask", { id, maskUnits: "userSpaceOnUse", x: 0, y: 0, width: W, height: H }, defs);
  mk("rect", { x: 0, y: 0, width: W, height: H, fill: `url(#${id}g)` }, m);
  const g = mk("g", { class: "ghost", mask: `url(#${id})` }, parent);
  mk("path", { d: r.d }, g);
}
/** A field of dots on the ground, fading out from the centre: the floor the object stands on. */
function floor(parent, K, x0, y0, x1, y1, step = 10) {
  const g = mk("g", {}, parent), cx = (x0 + x1) / 2, cy = (y0 + y1) / 2, R = Math.max(x1 - x0, y1 - y0) / 2;
  for (let x = x0; x <= x1; x += step) for (let y = y0; y <= y1; y += step) {
    const d = Math.hypot(x - cx, y - cy) / R;
    if (d > 1) continue;
    const [sx, sy] = K.P(x, y, 0);
    mk("circle", { cx: sx.toFixed(2), cy: sy.toFixed(2), r: 0.55, fill: TONE.edge, opacity: (0.55 * (1 - d * d)).toFixed(2) }, g);
  }
  return g;
}
/** A leader from a world point to a label: a thin rule, then the text. */
function leader(parent, from, to, lines, { anchor = "start", cls = "dash nf" } = {}) {
  mk("path", { d: `M${from[0]} ${from[1]}L${to[0]} ${to[1]}`, class: cls }, parent);
  mk("circle", { cx: from[0], cy: from[1], r: 1.6, ...(cls.includes("acc") ? { class: "accf" } : { fill: TONE.edge }) }, parent);
  const dx = anchor === "start" ? 5 : -5;
  lines.forEach(([text, role, opts], i) => type(parent, to[0] + dx, to[1] + 3 + i * 11, text, role, { anchor, ...opts }));
}
