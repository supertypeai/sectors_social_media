#!/usr/bin/env node
/**
 * Renders one Sectors Hairline slide to PNG.
 *
 *   node iso/hl/render.mjs <slide> <data.json> --out <file.png> [--html]
 *
 * <slide> is a file in iso/hl/slides (without .js). The page is: the Hairline kernel, style.js, DATA,
 * the slide, all in one script, drawing into a 360 × 450 svg shown at 1080 × 1350.
 */
import { existsSync, mkdirSync, readdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { dirname, join, resolve } from "node:path";
import { tmpdir } from "node:os";
import { fileURLToPath } from "node:url";
import { parseArgs } from "node:util";
import { launch } from "../vendor/browser.mjs";

const here = (p) => fileURLToPath(new URL(p, import.meta.url));
const { values, positionals } = parseArgs({ allowPositionals: true, options: { out: { type: "string" }, html: { type: "boolean" }, video: { type: "string" } } });
const [slide, dataFile] = positionals;
if (!slide || !dataFile || !values.out) {
  console.error("usage: node iso/hl/render.mjs <slide> <data.json> --out file.png [--html]");
  process.exit(2);
}

/** slides/<name>.js, or the same file name anywhere under slides/ (slides are grouped in folders). */
function findSlide(name) {
  const direct = here(`./slides/${name}.js`);
  if (existsSync(direct)) return direct;
  const walk = (dir) => {
    for (const e of readdirSync(dir, { withFileTypes: true })) {
      const p = join(dir, e.name);
      if (e.isDirectory()) { const f = walk(p); if (f) return f; } else if (e.name === `${name}.js`) return p;
    }
    return null;
  };
  const found = walk(here("./slides"));
  if (!found) throw new Error(`slide not found: ${name}`);
  return found;
}

const kernel = readFileSync(here("../vendor/kernel.js"), "utf8").replace(/^export \{ HL \};?\s*$/m, "");
// DATA.format "story" draws on a 360 × 640 page shown at 1080 × 1920 (Instagram story); anything else is 4:5
const dataText = readFileSync(dataFile, "utf8").trim();
const format = JSON.parse(dataText).format === "story" ? "story" : "feed";
const [VW, VH, PW, PH] = format === "story" ? [360, 640, 1080, 1920] : [360, 450, 1080, 1350];
// DATA.theme "light": every dark-theme colour in style.js, charts.js and the slide is swapped for its
// Supertype Foundations light-theme counterpart in one pass (latte ground, white cards, dark ink).
const LIGHT = {
  "#141210": "#faf8f3", "#1e1b18": "#f1ede4", "#272421": "#ffffff", "#322e2a": "#ebe7e0", "#48423d": "#cfc8ba",
  "#8a827b": "#9a9187", "#efece7": "#221d19", "#a19b8c": "#5c5449", "#6b645e": "#8f877e", "#f2efe9": "#ffffff",
  "#e4e0d8": "#2e2823", "#d9d5cc": "#3a332d", "#d6d3d1": "#3a332d",
  "#81a789": "#5f8f6a", "#b2d2b9": "#3d6b48", "#c07159": "#c4664a", "#dc8d74": "#a5462c", "#74a3be": "#3f7594", "#d0326f": "#9d0142", "#c59920": "#9a7412",
  "#5f7d66": "#4d7558", "#6f8f76": "#4d7558", "#c5dccb": "#9cc3a6", "#8f5444": "#a2523b", "#d9a090": "#e9b9a9",
  "#6c746e": "#c3bdb2", "#4b524d": "#aaa397", "#4a524c": "#aaa397", "#9aa59c": "#e4ded4",
  "#262320": "#e4ded3", "#1f1d1a": "#d3ccc0", "#2e2b27": "#ece7de",
};
// DATA.theme "blue": the same dark design on a deep navy-teal ground, with a mint buy and a rose sell.
const BLUE = {
  "#141210": "#0b1820", "#1e1b18": "#12252e", "#272421": "#13262f", "#322e2a": "#1a3440", "#48423d": "#2b4753",
  "#8a827b": "#6f8a95", "#efece7": "#eef5f6", "#a19b8c": "#8ea6af", "#6b645e": "#56707b",
  "#e4e0d8": "#dfe9ec", "#d9d5cc": "#cfdde1", "#d6d3d1": "#cfdde1",
  "#81a789": "#3fc99a", "#b2d2b9": "#7fe3bf", "#c07159": "#e0566b", "#dc8d74": "#f28d9b",
  "#5f7d66": "#24886a", "#6f8f76": "#24886a", "#c5dccb": "#b6f0da", "#8f5444": "#9a3444", "#d9a090": "#f5c2ca", "#e9b9a9": "#f5c2ca",
  "#6c746e": "#4f6873", "#4b524d": "#33505c", "#4a524c": "#33505c", "#9aa59c": "#8fa9b2",
  "#262320": "#16303a", "#1f1d1a": "#122630", "#2e2b27": "#1c3742",
};
const swapper = (map) => (s) => s.replace(/#[0-9a-fA-F]{6}\b/g, (h) => map[h.toLowerCase()] ?? h);
const lighten = swapper(LIGHT);
const theme = JSON.parse(dataText).theme;
const themeOf = theme === "light" ? lighten : theme === "blue" ? swapper(BLUE) : (s) => s;
// Every slide signs off with "sectors.app": the Sectors mark (logos/_sectors_mark.png, cropped from the app's
// logo) is set just left of each such text, whatever slide drew it, sized to the text.
const markFile = here("../../logos/_sectors_mark.png");
const MARK = existsSync(markFile) ? `data:image/png;base64,${readFileSync(markFile).toString("base64")}` : "";
const BRAND = MARK ? `for (const t of [...svg.querySelectorAll("text")].filter((t) => t.textContent.trim() === "sectors.app")) {
  const b = t.getBBox(), h = b.height * 0.92, w = h * 199 / 240, a = t.getAttribute("text-anchor") || "start";
  const x = a === "end" ? b.x - w - 3 : b.x - w - 3;
  if (a === "start") t.setAttribute("x", +t.getAttribute("x") + w + 3);
  const im = document.createElementNS(SVGNS, "image");
  im.setAttribute("href", "${MARK}");
  im.setAttribute("x", a === "start" ? b.x : x); im.setAttribute("y", b.y + (b.height - h) / 2);
  im.setAttribute("width", w); im.setAttribute("height", h);
  t.parentNode.insertBefore(im, t);
}` : "";
const script = [kernel, `const FORMAT = "${format}";`, themeOf(readFileSync(here("./style.js"), "utf8")), themeOf(readFileSync(here("./charts.js"), "utf8")), readFileSync(here("./objects.js"), "utf8"), readFileSync(here("./units.js"), "utf8"),`const DATA = ${dataText};`,
  themeOf(readFileSync(findSlide(slide), "utf8")), BRAND, "document.body.dataset.ready = '1';"].join("\n;\n");
// The whole drawing is wrapped in __draw(PROG): PROG is the animation progress, 0 → 1 (1 = the finished still).
// A still renders once at 1; --video renders every frame by redrawing the page at each PROG.
const page = `<!doctype html><html><head><meta charset="utf-8">
<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Inter+Tight:wght@200..800&display=swap">
</head><body><svg id="slide" xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ${VW} ${VH}" width="${PW}" height="${PH}"></svg>
<script>window.onerror = (m, s, l, c, e) => { document.body.dataset.error = (e && e.stack) || String(m); };</script>
<script>window.__draw = (PROG) => { document.querySelector("svg#slide").innerHTML = "";\n${script}\n};
document.fonts.ready.then(() => { try { window.__draw(1); } catch (e) { document.body.dataset.error = e.stack || String(e); } });</script></body></html>`;

const out = resolve(values.out);
mkdirSync(dirname(out), { recursive: true });
// the page is only kept next to the PNG with --html; otherwise it goes to the OS temp folder
const htmlFile = values.html ? out.replace(/\.png$/, ".html") : join(tmpdir(), `hl-${process.pid}-${Date.now()}.html`);
writeFileSync(htmlFile, page);

const browser = await launch();
try {
  const tab = await browser.newPage({ viewport: { width: PW, height: PH }, deviceScaleFactor: 1 });
  const errors = [];
  tab.on("pageerror", (e) => errors.push(e.message));
  await tab.goto(`file://${htmlFile}`);
  await tab.waitForFunction(() => document.body.dataset.ready || document.body.dataset.error, null, { timeout: 45000 }); // big embedded photos and webfonts can be slow
  const err = await tab.evaluate(() => document.body.dataset.error);
  if (err || errors.length) throw new Error(err || errors.join("\n"));
  if (values.video) {
    // --video <seconds>: PROG runs 0 → 1 over the first 75% (eased by the slide), then the finished frame holds
    const secs = Number(values.video) || 6, fps = 30, n = Math.round(secs * fps), frames = join(tmpdir(), `hl-frames-${process.pid}`);
    mkdirSync(frames, { recursive: true });
    for (let i = 0; i < n; i++) {
      const p = Math.min(1, i / (n * 0.75));
      await tab.evaluate((pr) => window.__draw(pr), p);
      await tab.locator("svg#slide").screenshot({ path: join(frames, `f${String(i).padStart(4, "0")}.png`) });
    }
    const mp4 = out.replace(/\.png$/, ".mp4");
    const { spawnSync } = await import("node:child_process");
    const r = spawnSync("ffmpeg", ["-y", "-loglevel", "error", "-framerate", String(fps), "-i", join(frames, "f%04d.png"),
      "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-movflags", "+faststart", mp4], { stdio: "inherit" });
    if (r.status !== 0) throw new Error("ffmpeg failed");
    rmSync(frames, { recursive: true, force: true });
    console.log(mp4);
  }
  await tab.evaluate(() => window.__draw(1));
  await tab.locator("svg#slide").screenshot({ path: out });
  console.log(out);
} finally {
  await browser.close();
}
if (values.html) console.log(htmlFile);
