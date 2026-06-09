# Sectors Social Posts — Visual Style Guide (Dark Variant)

A self-contained spec for the dark "IDX Filings" Instagram carousel family.
Everything here is a concrete value — canvas size, margins, pixel coordinates,
radii, border widths, opacities, font sizes, hex colors, and chart settings —
so the look can be reproduced in any tool (Figma, code, or an image prompt)
without reference to the original implementation.

All pixel values assume the native **1080 × 1350** canvas. Scale proportionally
for other sizes.

---

## 0. Design Philosophy (why the rules exist)

**The 2-second glance test.** A non-finance viewer scrolling a feed must "get"
the post in about two seconds. Clarity always beats decoration. Three consequences
that override aesthetics:

1. **Plain language.** Headlines read like a sentence a friend would say —
   "now owns over 5% of RISE", "profit jumped +428%". No jargon.
2. **Money is spelled out in headlines/subheads** — "Rp 11.9 billion", not
   "Rp 11.94B". Compact suffixes (Rp 2.30T, 14.28M) are only used inside tight
   spaces: stat-card values and chart labels.
3. **Color = meaning, never decoration.** Green = up/buy/good, orange-red =
   down/sell/bad — and it is **direction-aware**: a stock that fell *after a
   sale* is a good exit and is shown **green**, not red.

One big idea per slide. Lots of dark negative space. Only the single most
important number is allowed to glow in an accent color.

---

## 1. Canvas, Grid & Spacing

| Token | Value | Meaning |
|---|---|---|
| Canvas | **1080 × 1350 px** | Instagram 4:5 portrait. |
| Outer margin `M` | **76 px** | Left/right safe edge for cards, charts, dots. |
| Text inset `HX` | **108 px** (= M + 32) | Left edge for all headline/eyebrow/body text. Text is inset 32px *further* than cards, so copy sits visually inside the column. |
| Footer keep-clear | bottom **~110 px** | The footer (logo + social handles) is part of the background art. Never place content here. |
| Column gap (stat grid) | **18 px** | Gap between the three bottom cards. |
| Stat card width | **≈ 297 px** (= (1080 − 2·76 − 2·18) / 3) | Three equal columns across the safe width. |

### Canonical vertical rhythm (Slide 1)

```
 y=56    Header pills (left)  ·····  Logo(s) (right)        pill height 48
 y=132   Eyebrow subtitle  (accent color)   "TICKER · period · context"
 y=184   HEADLINE line 1  (subject)
 y≈244   HEADLINE line 2  (action — one word recolored to accent)
 y≈300   Subhead  (spelled-out money / plain context)
 │
 │            ░░░  CHART  (transparent, vertically centered)  ░░░
 │
 y=1000  ┌ Stat ┐  ┌ Stat ┐  ┌ Stat ┐         card height 164
 y=1180  · ●          page dots (centered)
 y≈1240  [ background footer — keep clear ]
```

### Slide 2 rhythm
Drop the headline block. Place the **second chart** higher (top ≈ **y=250**,
height ≈ **470**), then the stat trio (top = chart bottom + 26), then a single
**insight strip** below that (top = stat bottom + 22). Page dots stay at y=1180.

**Spacing principles**
- Headline line spacing: **+10 px** between the two lines (`font size + 10`).
- Subhead sits **~18–24 px** below the headline block.
- Cards never touch the outer margin; charts span the full safe width (`M` to `W−M`).
- The stat trio is always bottom-anchored in the same band so swiping feels rhythmic.

---

## 2. Color Palette

### Background
A dark, near-black vertical gradient with a faint **warm magenta/ember glow**
rising from the bottom third. Top reads almost pure black; the bottom carries a
subtle plum warmth. All cards are semi-transparent so this gradient shows through.

### Surfaces, borders & lines
| Name | Value | Use |
|---|---|---|
| Ink-Glass card fill | **rgba(20, 20, 24, 0.30)** | Every card, pill, chip, and split bar. Always composited *over* the background (not opaque) so the gradient bleeds through. |
| Hairline border | **#28282e** | Card & pill outlines. Width **2 px** on big cards, **1 px** on chips/inner cards. |
| Row divider | **#32323a @ 80/255 alpha**, **1 px** | Separators between list/roster rows. |
| Accent underline | accent color **@ 90/255 alpha**, **3 px** | The rule under a card title. |
| Split-bar track | **rgba(255, 255, 255, 0.094)** (≈ 24/255), radius 9, **18 px tall** | Background of buy/sold ratio bars. |

### Text colors
| Name | Value | Use |
|---|---|---|
| Headline white | **#FFFFFF** | Primary headline, card titles. |
| Soft cloud | **#C8C8D8** | Subheads, secondary headline lines. |
| Warm bone | **#F0EBE0** | Stat values, emphasised numbers (an *off*-white, so the accent number stands apart). |
| Bone light | **#e8e8f0** | Insight-strip values, chart in-bar labels. |
| Cool label | **#c0c0d0** | Chart axis labels, tertiary table numbers. |
| Muted lilac-grey | **#9090a8** | Sub-labels, column headers, "+N more". |
| Muted lilac (softer) | **#8888a0** | Stat sub-labels. |
| Disabled grey | **#555566** | "flat"/"unchanged"/empty stat values. |

### Semantic / directional accents
| Name | Value | Meaning |
|---|---|---|
| Signal lime — **buy / up / good** | **#A6D94E** | Buying, accumulation, positive YoY, "stock up". |
| Ember orange-red — **sell / down / bad** | **#F46D43** | Selling, distribution, negative YoY, "stock down". |
| Spectral blue — **market / total** | **#3288BD** | Market-price line **and** the right-hand "TOTAL money" stat chip. |
| Amber — **average** | **#FDAE61** | Avg / per-share references, avg-price dashed line. |
| Tag orange | **#F29942** | First (category) header pill, middle "secondary" stat chip, insight-module chips, filing-window markers. |
| Royal violet | **#5E4FA2** | Cross-stock post identity accent; avg-price line in some charts. |

### Series palettes (multi-entity charts)
- **Roster dots / cluster series** (Spectral): `#3288BD, #66C2A5, #ABDDA4,
  #FDAE61, #F46D43, #D53E4F, #5E4FA2`.
- **Cross-stock price lines** (dark-safe — avoids green/orange so lines never
  clash with buy/sell dot rings): `#4FC3F7, #CE93D8, #FFD54F, #F48FB1, #80CBC4,
  #B39DDB, #4DD0E1`.

### The coloring discipline
On the bottom stat grid, **values default to warm bone (#F0EBE0).** Only a
*directional ± metric* is ever colored — lime if up, ember if down (e.g. "STAKE
CHANGE +1.2", "PRICE NOW −48%"). Keeping everything else neutral makes the one
colored number read as *the* signal.

---

## 3. Typography

**Family: Inter** (weights: Bold, SemiBold, Medium, Regular, Italic). If Inter
is unavailable, fall back to a neutral grotesque (Arial/Helvetica) at the same
weights.

| Element | Weight · size (px) | Color | Notes |
|---|---|---|---|
| Header pill label | Bold · 22 | #FFFFFF | UPPERCASE. |
| Eyebrow subtitle | Bold · 24 | accent | `TICKER · period · context`. |
| Headline | Bold · **56–58**, auto-shrink to 34 | #FFFFFF | ≤ 2 lines. |
| Headline accent word | same size as headline | accent | One word/number recolored (ticker, "+428%"). |
| Subhead | SemiBold · 26–28 | #C8C8D8 | Spelled-out money / plain context. |
| Card title | Bold · 34 | #FFFFFF | "Who's Buying", "Where The Trades Happened". |
| Card count (top-right) | SemiBold · 26 | accent | "3 stocks". |
| Stat chip label | Bold · 17 | #FFFFFF | UPPERCASE, centered in outlined pill. |
| Stat value | Bold · **40**, auto-shrink to 26 | #F0EBE0 or directional | Centered. |
| Stat sub-label | Regular · 17 | #8888a0 | Title Case, centered. |
| Insight header | Bold · 18 | #9090a8 | "PAST INSIGHTS" / "GOOD TO KNOW". |
| Insight module label | Bold · 18 | module color | Color-bordered chip ("PAST RETURN", "WHY 5%?"). |
| Insight module value | SemiBold · 26 | #e8e8f0 | The one-line insight. |
| Column header (tables) | SemiBold · 18 | #9090a8 | UPPERCASE ("INSIDER", "SHARES", "VALUE (Rp)"). |
| Roster name | Bold · 28–30 | #F0EBE0 | List rows. |
| Roster sub-line | Regular · 18 | #9090a8 | "3 filings · Dec 2025 · owns 74.42%". |
| Roster numbers | SemiBold · 31 | #c0c0d0 (shares) / #F0EBE0 (value) | Right-aligned. |
| Rank number | Bold · 22 | #9090a8 | Left of each cross-stock row. |
| Direction chip | Bold · 15 | #FFFFFF | "Bought"/"Sold", 1px directional border. |
| Caption ("+N more") | Italic · 20 | #9090a8 | Overflow note. |

**Casing rules:** pill labels, chip labels, and column headers are UPPERCASE;
sub-labels are Title Case; headlines and subheads are sentence case.

---

## 4. Components — exact geometry

### 4.1 Glass pills (the signature element)
- Shape: **fully rounded** (corner radius = height / 2). Height **48 px**.
- Fill: Ink-Glass (rgba 20,20,24,0.30), composited over bg.
- Border: **2 px**, colored.
- Text: Bold 22, white, inset **22 px** from left, vertically centered.
- Width: `text width + 44` (+ 30 if it carries an arrow).
- Optional arrow: a small filled **triangle**, size ~7px, **13 px** right of the
  text, pointing up (▲) or down (▼) in the border color.
- **Pairing:** two pills top-left at `y=56`, separated by a **16 px** gap.
  - **Left pill** = category — **tag-orange (#F29942)** border
    (e.g. `INSIDER`, `INSIDER CHAIN`, `MAJOR SHAREHOLDER`, `EARNINGS SPIKE`).
  - **Right pill** = status/direction — **accent** border, usually with arrow
    (`CROSS STOCKS`, `CHAIN SELL ▼`, `PASSED 5% ▲`, `+428% vs last year ▲`).

### 4.2 Header logos
- Circular, masked to a clean circle with a thin **white ring (#eeeeee, 1 px)**.
- Size **62 px** (single) / **56 px** (multi-stock).
- Anchored top-right: right edge at `1080 − 76 − 32`, vertically centered on the
  pill row.
- Multiple logos overlap right-to-left, stepping **logo size + 14 px** left each.

### 4.3 Stat cards (bottom trio)
- Size: width ≈ 297, **height 164**, corner radius **22**.
- Fill Ink-Glass; border hairline **#28282e, 2 px**.
- **Centered three-part stack:**
  1. **Chip label** at top: outlined pill, height **30**, radius = 15
     (fully round), **1 px** accent border, label Bold 17 white. Chip top at
     card `y + 22`; chip width = `label width + 28`, horizontally centered.
  2. **Value** at card `y + 70`: Bold 40 (auto-shrink to 26 to fit width − 24),
     centered, warm bone `#F0EBE0` — or a directional color if it's a ± metric.
  3. **Sub-label** at card `y + 126`: Regular 17, Title Case, `#8888a0`, centered.
- **Fixed chip-color order across the trio** (both slides, for consistency):
  **left = accent ("what") · middle = tag-orange ("secondary") · right =
  spectral-blue ("the TOTAL money").**

### 4.4 Content card (roster / "where the trades happened")
- Large Ink-Glass panel, radius **22**, hairline border (1–2 px).
- Inner padding **32 px**.
- Title row: Bold 34 white on the left; accent-colored count (SemiBold 26) on
  the right (e.g. "3 stocks").
- A **3 px accent underline at 90/255 alpha** spans the inner width, ~52 px
  below the title top.
- Column headers (SemiBold 18, #9090a8) ~20 px under the underline.
- **Rows** (roster row height **118 px**; cross-stock row height **132 px**):
  - Optional rank number (Bold 22, #9090a8) at the left.
  - A colored series **dot** (18 px) *or* a circular logo (50 px).
  - Name (Bold 28–30, #F0EBE0) + a muted `·`-joined meta line (Regular 18,
    #9090a8) beneath it.
  - Right-aligned numbers: shares (SemiBold 31, #c0c0d0), value (SemiBold 31,
    #F0EBE0).
  - Between rows: a **1 px #32323a divider at 80/255 alpha** (omit after the
    last row).
- Overflow: "+N more …" in Italic 20, #9090a8.

### 4.5 Direction chip (inline, in rows)
- Small rounded tag, radius **10**, height **28 px**.
- Ink-Glass fill + **1 px** directional border (lime buy / ember sell).
- Label Bold 15 white, inset ~11 px.

### 4.6 Buy/Sold split bar (mixed-direction posts)
- Track: rounded rect radius **9**, height **18 px**, fill rgba(255,255,255,0.094).
- Segments drawn as thick **18 px** lines in the directional color at ~230/255
  alpha, widths proportional to value.
- Legend below: 10 px color dots + "Bought Rp …" / "Sold Rp …" labels
  (SemiBold 17, #c8c8d8).

### 4.7 Insight strip (slide-2 footer card)
- Ink-Glass panel, radius **22**, **1 px** hairline border. Inner padding 28 px,
  row height 64 px.
- Header (Bold 18, #9090a8): "PAST INSIGHTS" or "GOOD TO KNOW".
- Each module = a **color-bordered chip** (radius 10, height 34, 1 px border in
  the module color, label Bold 18 in that color) + a one-line value (SemiBold
  26, #e8e8f0) to its right. Keep to **≤ 2 modules**.

### 4.8 Page dots
- Centered horizontally at **y = 1180**.
- Dot diameter **14 px**, gap **12 px**.
- Active dot = **accent**; inactive = **#44445a**.

---

## 5. Charts

Charts are rendered on a **transparent** background and composited onto the
gradient, so they feel painted directly on the canvas (no chart "box"). General
recipe:

**Frame & grid**
- Figure & axes backgrounds fully transparent (no fill).
- Hide **top and right** spines. Left and bottom spines: **#555**.
- Grid: dashed lines, color **#444**, alpha **0.18–0.22**.
- Tick labels: **#c0c0d0**, size **10–11**. X-dates formatted like "Dec 2025"
  ("%b %Y") for wide spans, "12 Dec" / "%d %b" for narrow ones — never repeat the
  same month label.
- Axis title: left-aligned, **#e8e8f0**, bold, size **12**, e.g.
  "Profit (IDR billion, each quarter)", "Cumulative sold (Rp)". Y-values use
  thousands separators or `+%.0f%` for returns.
- Export at **DPI 130**, tight bounding box, transparent.

**Lines & areas**
- Market-close / price line: **spectral blue #3288BD**, width **2.2** (a lighter
  **#7FB3D5** variant when paired with a soft fill).
- Optional price area fill: **#3288BD at alpha 0.08**.
- Average-price reference: **#5E4FA2** (or amber), **dashed**, width 1.6.
- Threshold line (e.g. the 5% ownership line): **accent, dashed, width 1.8**,
  with a faint accent `axhspan` band above it at **alpha 0.07** and a small bold
  accent label.
- "Buy-zone" shading over a filing window: accent fill at **alpha 0.10**;
  filing-window boundaries as **#F29942 dashed** verticals at alpha ~0.55.

**Markers (trades)**
- Scatter dots sized **150–280**, filled with the series color and a **2–2.8 px
  directional ring**: **lime #A6D94E = buy**, **ember #F46D43 = sell**. White
  edge on single-series charts.
- Same-day trades fan out horizontally so stacked dots stay visible.
- A "bought here" dot uses the accent fill + white edge + a small bold accent
  annotation above it.

**Bars (earnings)**
- Bar width **0.66**. Context quarters fade to **alpha 0.28**; the two compared
  bars (same-quarter-last-year and now) are full opacity.
- "Now" bar = accent (lime up / ember down); "last year" bar = **#9aa0ad**.
- In-bar value labels: highlighted bars bold size 12 **#f0ebe0**; context bars
  size 9 **#6f6f80**.
- The headline % change is annotated above the "now" bar in bold accent, size 14.
- Single baseline: the bottom frame *is* the zero line; only drop below zero when
  a bar is actually negative.

**Legends**
- Frameless, placed below the plot, label color **#c0c0d0**. Direction legend
  shows hollow dots with lime/ember rings labelled "Buy"/"Sell".

---

## 6. Post Layout Pattern (any new type)

Every dark post is a **two-slide carousel**: Slide 1 *hooks* (what happened),
Slide 2 *proves* (is it real / the detail).

1. **Header pills**: `[CATEGORY]` (orange border) + `[STATUS ▲/▼]` (accent border).
2. **Eyebrow** (accent): `TICKER · <period or "latest quarter"> · <sector/context>`.
3. **Headline** (≤ 2 lines, plain English): subject line, then an action line
   with the single most important number/ticker recolored to accent.
4. **Subhead** (soft cloud): spelled-out money or one plain-English clarifier.
5. **Chart** spanning the safe width, vertically centered in the middle band.
6. **Stat trio** at y=1000: chip colors accent / orange / blue; values warm bone,
   only ± metrics colored.
7. **Page dots** at y=1180.
8. Slide 2: second chart up top → stat trio → insight strip ("GOOD TO KNOW" /
   "PAST INSIGHTS", ≤ 2 modules).

**Existing types** (for reference): insider cluster (many insiders, one stock),
insider chain (one insider buying repeatedly), insider cross-stock (one holder
across many stocks, violet accent), becoming-insider (crossing the 5% ownership
line), earnings spike/drop (profit vs same quarter last year).

---

## 7. Build Checklist

- [ ] 1080×1350; dark gradient bg; bottom ~110px left clear for the baked footer.
- [ ] Two slides; page dots at y=1180; slide 1 hooks, slide 2 proves.
- [ ] Header = orange category pill + accent status pill (▲/▼ if directional), y=56, h=48, fully rounded.
- [ ] Logo(s) top-right, circular with 1px white ring.
- [ ] Eyebrow in accent at y=132; headline Bold 56→34 at y=184, one accent word; subhead SemiBold 26–28 in #C8C8D8.
- [ ] Money spelled out in headline/subhead; compact suffixes only in stats/charts.
- [ ] Charts transparent, spectral-blue price line, lime/ember directional dot rings, dashed #444 grid.
- [ ] Stat trio: cards 297×164, radius 22, Ink-Glass + #28282e border; chips accent/orange/blue; values #F0EBE0, only ± metrics colored.
- [ ] Cards radius 22, chips radius 10, pills fully rounded; borders 1–2px; row dividers #32323a 1px.
- [ ] Color is meaning and direction-aware (a fall after a sale is green).
- [ ] Passes the 2-second glance test.
