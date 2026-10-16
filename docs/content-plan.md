# Sectors social content plan

Three tracks that share one visual language (the Sectors Hairline style, see `iso/hl/` and
`iso/hl/OBJECTS.md`) and one render step (data as JSON → PNG or MP4).

**Why:** automated posts average **1.2** engagement, manual posts **8.2** (Instagram 14.3). The best
performers are person/holdings stories. Source: Mailroom analysis
`social-automation/mailroom/tmp/social-analysis-2026-10-12/README.md`.

**Copy language:** English.

---

## Track 1 — Automated posts

Cron-generated, posted only when something is worth posting, at most 1 a day. Replaces today's
~30 templated types with 8, about 10–14 posts a week.

Every post: a number plus a comparison, a person or a ticker, and a question at the end.

| # | Post type | Data | Example hook | Cadence |
|---|---|---|---|---|
| 1 | **Big insider move** (cluster, chain, becoming-insider and cross-stock merged) | `idx_filings` | "Why would Low Tuck Kwong sell 30% of Bayan in a single day?" | when triggered, ≤1/day |
| 2 | **Sold below market / odd price** | filings + `idx_daily_data` | "Sold at Rp 2,588. The market closed at Rp 12,550." | rare, high impact |
| 3 | **Drawdown explainer** (IHSG slump) | `idx_daily_data` | "BBCA's 7th straight foreign net-sell day" | 2–3/week while falling |
| 4 | **Who owns it** | `idx_company_report.major_shareholders` | "One family owns 92%. You can trade 8%." | 2/week |
| 5 | **Ranking of the week** | daily data + company report | "5 LQ45 stocks at a 5-year low" | 1/week |
| 6 | **Earnings, only when extreme** | `idx_company_report` | "Profit +473%, the biggest jump in its sector" | when triggered |
| 7 | **Save-worthy calendar** (dividends, AGMs, IPOs) | `idx_agm`, dividend data | "12 dividends to collect this month" | monthly |
| 8 | **Weekly roundup** | daily + broker data | "IHSG −4.5% this week: who's selling?" | 1/week |

**Cut or merged:** plain daily filings, single AGM posts (→ #7), broker-trending and volume-spike
singles (→ #8), image crossposts to Threads.

### Rules that keep it from feeling automated
- Post when something happens, not on a clock. Each candidate gets a "worth posting?" score.
- The headline is the point, written per post from the data. Numbers come only from the data.
- The visual changes because the numbers change (a stake drawn as many objects, kept vs sold).
- Recurring posts are named series on purpose (e.g. the weekly roundup).

### Carousel format (post type #1)

| Slide | Content |
|---|---|
| 1 · Hook | question headline + sector object (kept solid, sold as a dashed ghost) + stats strip + logo chip |
| 2 · Proof | one chart: trade price vs market close (shown only when ≥15% apart) |
| 3 · Who owns it now | ranked shareholders, the mover highlighted with "was X%" |
| 4 · Takeaway | three numbers + a closing question + CTA + "Not financial advice" |

### Sector objects
One object per sector, drawn as **many of the object itself** (minimal style). The kept part is solid, the sold part a quiet dashed ghost. Rules are in `iso/hl/OBJECTS.md`.

The sector split is based on the 181 big insider moves over 180 days.

| Sector | Big moves | Object | Status |
|---|---|---|---|
| Basic Materials | 31 | ingots | prototype |
| Consumer Cyclicals | 27 | shopping bags | prototype |
| Consumer Non-Cyclicals | 22 | grocery crates | prototype |
| Industrials | 20 | machine blocks / gears | planned |
| Financials | 16 | vault / gold bars | planned |
| Energy | 15 | mine cart | built (single object) |
| Properties & Real Estate | 15 | tower blocks | planned |
| Infrastructures | 12 | telecom towers | planned |
| Transportation & Logistic | 12 | containers | planned |
| Technology | 7 | server racks | planned |
| Healthcare | 4 | pill bottles | planned |

Without an object yet, a sector falls back to a stake bar plus the logo.

**Status:** #1 builder exists (`image_generator/insider_move.py`). Not yet on cron, no captions,
not on the Mailroom queue. Nothing auto-posts without approval.

---

## Track 2 — Semi-automated story images (~2/week)

```
Detector (auto) → digest: 3–5 story candidates with the facts pulled
      ↓
Person picks one, writes the angle in 1–2 lines
      ↓
Claude builds a one-off detailed figure (/anatomy style) from a shared parts library
      ↓
Person reviews (2-second "emak-emak" test) → queue
```

**Carousel shape:**
1. The whole object plus a hook line.
2. Slides 2–4: zoomed-in crops, one fact each.
3. The last slide: the "so what" plus the CTA.

**Ideas**
- Lo Kheng Hong's portfolio as a **chest of drawers**, each drawer as deep as his stake.
- Conglomerate families (Hartono, Salim, Sinarmas) as a **gearbox**.
- The state funds as a **water manifold** feeding money into stocks.
- IPO lock-up expiry as a **time-lock safe**.
- Free float as a **valve**: how much of a stock can actually trade.

Effort: about 1–2 h of Claude work plus about 15 min of a person's time per post.

---

## Track 3 — Semi-automated videos (/isostory, 1/week to start)

```
Detector → digest → person picks + angle
      ↓
Claude writes a storyboard (t | beat | motion | text | subtitle) → person approves
      ↓
Story file → look check → render → 9:16 MP4 + SRT + poster
      ↓
Optional voiceover → queue as a Reel
```

Each Reel is 15 s with a hook by 0.6 s, 3–4 beats and an end card. Subtitles are always on.

| Story shape | Scene | Used for |
|---|---|---|
| **The Accumulation** | a container filling up past the 5% line | chain buys, becoming-insider |
| **The Exit** | the same container draining | insider selling |
| **The Pile-on** | several people feeding one vault | cluster buys |
| **The Web** | camera pulling back through an ownership network | conglomerates, cross-stock |
| **Before/After** | a machine running slow, then fast | earnings |

There's no video data yet, so each Reel is measured against the manual-post average of **8.2**.

---

## How the tracks connect

```
        shared: Hairline style · sector objects · JSON → PNG/MP4 render step
             │                    │                       │
  Track 1 (auto, ≤1/day)  Track 2 (images, 2/wk)  Track 3 (video, 1/wk)
             ↑_____ formats that prove themselves graduate to automation _____│
```

Tracks 2 and 3 are where new formats get tried by hand. Shapes that work move into Track 1 as
automated templates. The sector objects built for Track 1 also feed the Exit and Accumulation videos.
