# Automated posts: one system, 8 post types

Status: design spec (2026-10-13). This merges the eight post-type designs into one system.
Format: English copy, 1080x1350 carousel, 3-5 slides, "Sectors Hairline" style (`iso/hl/style.js`).
Why: the old ~30 templated automated types average 1.2 engagement and manual posts average 8.2. What works: a person, a rupiah amount and a ticker; a number with a comparison; rankings; ending on a question.

The rule behind this spec: **build 8 components once and reuse them in every post.** A new post type is a new data selector plus a slide list. It never needs a new drawing.

---

## 1. Shared component kit (8 components)

| # | Component | Shows | Inputs | Used by | Status |
|---|---|---|---|---|---|
| C1 | **NUMBER.hero** | Huge light numeral, tracked-caps kicker, one title line with one accent word. A `pair` variant shows two numerals side by side with one accented (this streak vs record, now vs year ago) | `value, unit, kicker, title, sub?, accent, pair?: {a, b, labels}` | all 8 | **New file.** The pattern already lives inside `pricegap.js` / `takeaway.js`, so extract it |
| C2 | **UNITS.field** | A part-of-whole as countable units. Unit = `square` (100-grid waffle, 1 per %) or `object` (N copies of a sector object). Kept units are solid, moved units are dashed ghosts (sell) or accent (buy) | `total, segments[{n, kind: kept/moved/new/other}], unit: square or object, sector` | #1, #4 | **Exists, needs merging.** `slides/waffle.js` + `slides/obj_bags_many.js` (+ crates/ingots `_many`), objects in `objects.js`, rules in `OBJECTS.md` |
| C3 | **CHART.gap** | Two values on one honest scale from 0, with the gap shaded in the accent | `a {value,label}, b {value,label}, gapLabel` | #1 (slide 2), #2 | **Exists**: `slides/pricegap.js`. Generalise the labels |
| C4 | **CHART.line** | One series with end dates labelled only. Options: one or more accent markers, a shaded window, a horizontal reference line, and `spark` mode (no axes, end dot) | `points[], markers?, window?, refLine?, spark?` | #2, #3, #5, #8 | **Exists**: `charts.js`, `slides/price_trades.js`. Add `window` + `spark` |
| C5 | **CHART.bars** | Hairline outline bars on one zero baseline, at most 2 highlighted, value labels in words. `pair` mode = 2 bars (before/now). `streak` mode = N small daily bars below or above zero | `bars[{label, value, hl?}], mode: history/pair/streak` | #3, #6, #8 (optional) | **New** |
| C6 | **LIST.ranked** | Up to 5 rows (6 in diverging mode): rank, name, numeral, true-scale hairline bar, right note. One accented row. `diverging` mode puts a centre line with bars growing left and right | `rows[{name, value, display, note, hl?}], diverging?` | #1, #3, #4, #5, #6, #7, #8 | **Exists**: `slides/ranked.js` / `ranked_focus.js`. Add `diverging` |
| C7 | **STRIP.week** | 5 day columns Mon-Fri on a hairline baseline, tickers stacked under their day, one day accented | `days[{date, items[]}], hlDay` | #7 | **New** (built last) |
| C8 | **CARD.takeaway** | At most 3 short facts, one plain-English line, the closing question and a sectors.app CTA | `facts[≤3], line?, question` | all 8 (closer) | **Exists**: `slides/takeaway.js` |

Shared beneath all of these: `frame()` / `style.js` (ground, brand strip at y≈1261, dots at 1180, CTA at 1235) and `fmt.moneyWords` (port `_money_words` → "Rp 4.1 trillion").

**Merges and cuts**
- `NUMBER.compare` (#3) → folded into C1 `pair`.
- `STREAK.bars` (#3) and `CHART.pair` (#6) → folded into C5 modes.
- `CHART.spark` (#8) → C4 `spark` mode.
- `SCALE.twoTick` (#2) is C3.
- `WAFFLE.100` (#4) and `OBJECT.many` (#1) → one C2 with two unit kinds.
- `TIMELINE.week` → C7.
- `CALENDAR.grid` was dropped because a month grid fails the glance test.
- Retired: `stake_split.js` (stacked column with 4 legends), `stake_before_after`, `stake_simple`, `shrink`, the `byan_*` and `coal_haul` explorations, and the `_A/_B/_C` object variants. Keep one drawing per sector object.

---

## 2. Matrix: post type × slide → component

| Post | S1 (hook) | S2 | S3 | S4 | S5 | Typical count |
|---|---|---|---|---|---|---|
| 1 Big insider move | C1 + C2 object | C3 *(if gap)* | C6 | C8 | – | 3-4 |
| 2 Sold below market | C1 + C3 | C4 *(1 marker)* | C1 (Rp left on table) | C8 | – | 3-4 |
| 3 Drawdown / streak | C1 + C5 streak | C4 *(window)* | C1 pair, or C6 (IHSG draggers) | C8 | – | 3-4 |
| 4 Who owns it | C2 square + C1 title | C6 | C1 (free float) | C8 | – | 3-4 |
| 5 Ranking of the week | C1 (count) + ticker strip | C6 | C4 *(refLine + dot)* | C8 | – | 3-4 |
| 6 Earnings extreme | C1 + C5 pair | C5 history | C6 (peers) | C8 | – | 3-4 |
| 7 Dividend week | C1 (top yield) | C6 | C7 | C8 | – | 3-4 |
| 8 Weekly roundup | C1 + C4 spark | C6 diverging (movers) | C6 diverging (foreign) | C6 brokers *(rare)* | C8 | 4-5 |

C6 is used most (7 types), then C1 and C8 (8 each). Building C1, C6 and C8 covers about 60% of all slides.

---

## 3. Post types

### 1 · Big insider move
One filing that moved ≥1 pp of a company. It absorbs the old cluster, chain, becoming-insider and cross-stock posts. Those now appear only as a kicker line ("his 4th sale this year").

- **Replaces:** `insider_patterns.py` group_* posts, `renderers/insider_dark.py`, `insider_social.yml`, `becoming_insider_social.yml`, `plain_filings_social.yml` (retire). Base code: `image_generator/insider_move.py`.
- **Data:**
  - `idx_filings`: pp before/after, value, price, `price_transaction` legs, `holder_type`.
  - `idx_company_report.major_shareholders`.
  - `fetch_daily_prices` for the close on the leg day.
  - `logos/`.
- **Trigger:** runs daily over 14 days of filings (`select_moves`). It posts only if pp ≥ 1.0 and value ≥ Rp 1 B.
  - Score = pp × log(value), plus bonuses for: paired deal or change of control, crossing 5%, being part of a chain or cluster, price gap ≥ 15%.
  - Cadence: ≤3 posts/week. Never the same symbol+holder twice within 30 days.
- **Hooks:** "12.4% of {Bank} changed hands in one deal" · "Prajogo Pangestu bought 3.1% more of BRPT: Rp 2.4 T in one filing".

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `{pp}%` + row of 12 sector objects with the moved ones ghosted or accented | C1 + C2 `object` | "{pp}% of {company} {sold/bought} by {holder}" · caps: `{SYM} · {before}% → {after}% · {date}` |
| 2 | Odd price *(only if \|gap\| ≥ 15%)* | the shaded gap | C3 | "Sold at Rp {p}, {gap}% below the Rp {close} close" |
| 3 | Who owns it now | the mover's row, "was {before}%" | C6 (≤5 rows) | "Who owns {SYM} now" |
| 4 | Close | Rp value | C8 | {pp}% · Rp {value} · {after}% now. Q: "Why would an insider {sell/buy} this much at once?" |

- **Skip when:**
  - any of `price` / `pct` is null;
  - the filing has mixed legs (`drop_mixed_leg_filings`);
  - it is a same-group internal transfer that is not framed as a change of control;
  - `amount_transaction` ≈ 0 (rights or conversion artefact).
  - Drop S3 if the roster has fewer than 3 holders or sums > 100%. Never invent "everyone else".
- **Risks:**
  - `price_transaction` is a VWAP across legs, so compare against the close on the leg day.
  - Holder-name merging can go wrong.
  - Paired-deal false matches.
  - 12 units can't show 0.4 pp. The numeral carries the precision and the objects show only the proportion of the holder's stake.

### 2 · Sold below market / odd price
A trade priced far from the screen. It promotes the pricegap slide into its own post. **If #1 already covers the filing, #1 wins** and #2 does not post.

- **Replaces:** the "market below filing price" footnotes in `insider_dark.py`, the `filings-plain` daily card, and the price-vs-cost idea from the lost `broker_support` post.
- **Data:**
  - `idx_filings`: VWAP = value / shares; the trade day is the last leg date; `tags` gives the stated purpose.
  - `fetch_daily_prices`: the trade-day close plus 6 months of closes.
- **Trigger:** runs daily over 3 days of filings. Fires when |VWAP / close − 1| ≥ 15% and value ≥ Rp 5 B.
  - Score = |gap| × log10(value) × 1.5 for the "odd" direction (sell below or buy above market) × 0.5 for plan-priced tags.
  - Cadence: ≤2/week, expect ~1. Some weeks there will be none.
- **Hooks:** "He sold at Rp 3,100. The market paid Rp 4,250 that day." · "Someone paid 40% ABOVE market for CUAN. Why?"

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `−27%` | C1 + C3 | "{Holder} sold Rp {v} of {Co} below the market price" · ticks: sale price / close on {date}. No stake line |
| 2 | Odd that day, not a slump | one accent dot far off the line | C4 (1 marker) | "The market never traded near Rp {p}". If the 6-month low is within 5%, switch to "Price had already fallen near Rp {p}" |
| 3 | In rupiah | `Rp 151 B` | C1 | "{shares} shares at Rp {p} instead of Rp {close}" · caps: STATED PURPOSE: {tag} |
| 4 | Close | question | C8 | stake {a}→{b}% · Buyer: {name} only if a matching filing exists, else "not disclosed" · close since. Q: "Why sell this cheap?" |

- **Skip when:**
  - the tag is mesop / award / inheritance / dividend / rights;
  - the filing has mixed legs, price > `MAX_SANE_PRICE`, or is a duplicate;
  - there is no close within 7 days, or median daily value is tiny;
  - gap > 90% (unit or split error);
  - fewer than 40 closes → drop S2.
- **Risks:**
  - Pasar-nego block trades are legitimately priced off the board. The copy says "below the market price that day" and never says "dumping".
  - Repo-tagged transfers.
  - Thin supply.

### 3 · Drawdown / streak explainer
A single subject: one stock's foreign-sell streak, or an IHSG slump.

- **Replaces:**
  - `anomalies_changes.py` (anomaly_changes_social.yml)
  - the `stock_performance.py` IHSG returns
  - `winners_losers` / `top_movers` daily losers
- **Data:**
  - `idx_daily_data`: close, foreign buy/sell volume. Net ≈ (buy − sell) × close.
  - `index_daily_data` for IHSG.
  - `idx_company_report` for the universe (top-100 by market cap).
  - **New** `fetch_drawdown_streak()`, which needs 1-2 years of history for "longest since".
- **Trigger:** runs daily after close.
  - (a) Stock: ≥5 straight net-sell days and outflow ≥ Rp 100 B (or price −7%).
  - (b) IHSG: ≥5% below its 60-day high, or ≥4 straight down days.
  - Score = 0.5 × record-ness + 0.3 × outflow rank + 0.2 × drop rank. Post when score ≥ 0.6.
  - Cadence: ≤2/week. Prefer IHSG when both fire. No repeat ticker within 10 trading days.
- **Hooks:** "BBCA: 7 straight days of foreign selling. Rp 2.1 T out." · "IHSG is 8.4% below its August high."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `7` beside 7 rose bars below zero | C1 + C5 `streak` | "{N} STRAIGHT DAYS OF FOREIGN NET SELLING" · "Rp {x} out since {date} (approx.)" |
| 2 | Price impact | shaded window on the line, one label | C4 `window` | "{close0} → {close1} ({pct}%)" |
| 3 | Is it unusual? | `7 vs 9` | C1 `pair` (IHSG variant: C6 "who dragged IHSG") | "Longest in {1y}: {N} now vs {max} ({date})" |
| 4 | Close | one sentence | C8 | "Foreign selling often ends when the price looks cheap again." Q: "Buy {T} here, or wait?" |

- **Skip when:**
  - any streak day has null foreign volume;
  - price rose over the streak;
  - a day moved > 30% (corporate action);
  - the streak broke before render.
  - Drop S3 when there is less than 1 year of history.
- **Risks:**
  - Volume × close is only approximate, so label it.
  - Fear framing.
  - Overlap with #5 and #8. Keep this post to one subject.

### 4 · Who owns it
- **Replaces:**
  - `renderers/ownership.py`, `ownership_social.yml`
  - `ownership_board.py`, which folds into #5 as a theme
  - Kept: `select_ownership_posts`, `select_ownership_fires`, `state/posted_ownership*.json`
- **Data:** `fetch_company_report_ownership` → `major_shareholders` (the "Public" row is the free float), plus `tags` single-entity-holding-70. Not used: `shareholders_composition`.
- **Trigger:** runs on unposted names, or when the controller's stake moved ≥ the change gate.
  - Score = recognisability (market-cap rank), boosted by an extreme controller stake or float < 10%, and by a recent controller filing.
  - Post only if rank ≤ 200 or float < 7.5%.
  - Cadence: 1/week.
- **Hooks:** "If BREN were 100 shares, one family would own 97." · "You can only really buy 6% of AMMN."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | the lit block in a 10×10 grid | C2 `square` + C1 title | "If {T} were 100 shares, {controller} owns {N}." · caps: {company} · {sector}. No legend |
| 2 | Names + money | controller row | C6 (≤4 rows; last row = Public) | "{holder} · {pct}% · Rp {value}" |
| 3 | So what | `{float}%` | C1 | "FREE FLOAT" · "IDX median ~{computed}%. Thin float = bigger swings on small orders." Optional line if the controller filed a trade within 90 days |
| 4 | Close | question | C8 | Q: "Would you buy a stock where one owner calls every shot?" |

Accent: ownership is not a buy or sell, so the controller block uses the brightest warm grey ("hi"), not teal or rose.

- **Skip when:**
  - no Public row, or the sum is outside 95-105%;
  - the controller holds < 50%;
  - it is the same SOE more than once a quarter;
  - rank > 300 unless float < 5%;
  - the ticker was posted in the last 6 months.
- **Risks:**
  - The snapshot is stale, so print "as of {date}" and never "today".
  - The controller may be a holding vehicle. Show the legal name and don't guess the person.
  - Nominee accounts.
  - Waffle rounding: floor the controller block and force at least 1 Public square.

### 5 · Ranking of the week
One theme, one list.

- **Replaces:**
  - `lq45_ytd.py` (lq45_ytd_social.yml)
  - the ownership-board leaderboard, which becomes a theme here
  - Plain weekly gainers and losers go to #8.
- **Data:**
  - `idx_company_report`: indices (LQ45), market-cap rank, sub_sector.
  - `idx_daily_data` close over 5 years, paginated.
- **Trigger:** runs Sat/Sun. Themes rotate: 5-year low / 52-week high / YTD worst / YTD best / most-controlled (ownership).
  - Score = qualifying count × extremeness.
  - Post only if ≥3 names qualify and #1 is in the top-50 by market cap. Never the same theme two weeks running.
  - Cadence: 1/week.
- **Hooks:** "5 LQ45 stocks just hit a 5-year low. One is BBRI."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `5` | C1 + muted ticker strip | "LQ45 STOCKS AT A 5-YEAR LOW" · {T1} · {T2} … |
| 2 | The list | #1 row in accent | C6 (≤5) | "{T} {company} · x% above 5y low · {sub_sector}" |
| 3 | Make #1 concrete | today's dot on the floor line | C4 `refLine` | "{T1}: lowest close since {date}" · Rp now vs Rp peak |
| 4 | Close | question | C8 | Q: "Cheap or broken? Comment a ticker." |

- **Skip when:**
  - fewer than 3 names qualify;
  - #1 is outside the top-50;
  - the theme or #1 ticker ran in the last 2 weeks.
  - Drop S3 if there is less than 2 years of history, or a day moved > 40%, since close is unadjusted and splits create fake lows.
- **Risks:**
  - Survivorship in LQ45 membership.
  - "5-year low" can read as buy advice.

### 6 · Earnings, only when extreme
- **Replaces:**
  - `select_earnings_spikes`, `render_earnings_spike_dark`
  - `cli.py earnings-report` / `earnings-spike-dark` / `earnings-drop-dark`
  - `earnings_social.yml`
  - Kept: `state/posted_earnings.json`
- **Data:** `fetch_company_report_earnings(200)` → `historical_financials_quarterly`.
  - YoY is **always recomputed**, never taken from the stored `yoy_quarter_earnings_growth`.
  - Peer median comes from the same frame grouped by sub_sector.
- **Trigger:** runs during reporting season.
  - Bands: spike +60…+800% with revenue also up, drop −40…−100% with base > 0. The base must be ≥ 10% of a typical quarter.
  - Score = 40 size + 25 recognisability + 20 gap vs peers + 15 record. Post when ≥ 60.
  - Cadence: ≤1/day, ≤3/week. Empty off-season weeks are fine.
- **Hooks:** "BBRI's profit fell 41%. Its banking peers? Down 3%." · "ADRO's biggest quarterly profit in 2 years: Rp 4.1 trillion."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `−41%` | C1 + small C5 `pair` | "{T} · Q{q} PROFIT" · "vs the same quarter last year" · bars: Rp x T → Rp y T |
| 2 | Is it real? | the accent bar among 6-8 quarters | C5 `history` | "Biggest profit in {N} quarters" only if it is truly the max, else "Profit, last {N} quarters" |
| 3 | vs peers | the company's row | C6 | "{T} vs other {sub_sector} companies" |
| 4 | Close | verdict line | C8 | Revenue verdict (broad boom / costs grew faster / may be a one-off). Q: "Would you buy {T} after this?" |

- **Skip when:**
  - the base is ≤ 0 or near zero, including loss→profit (a "back to profit" post is a separate copy, not a %);
  - growth is outside the bands;
  - the quarter is > 150 days old;
  - the stock is not top-150;
  - the whole sub-sector median is down > 30% (that's a sector story).
  - Drop S3 if fewer than 3 peers.
- **Risks:**
  - No publish date, so "just reported" can lag.
  - Bank revenue semantics differ.
  - Fiscal-quarter labels.

### 7 · Dividend week ahead
IPOs are out of scope because there is no source in the repo. AGMs get one line at most.

- **Replaces:** `upcoming_dividend.py` table (dividend_social.yml), `dividend.py` card, `agm.py` (agm_social.yml).
- **Data:**
  - `idx_upcoming_dividend` (dedupe by symbol + cum_date, keep the latest `updated_on`)
  - latest close from `idx_daily_data` → yield
  - `idx_company_report` (name, rank)
- **Trigger:** fixed slot Sunday evening, covering cum-dates in the next 7-10 trading days. Post if ≥3 payers with rank ≤ 300. Yield ≥ 3% counts double. Cadence: 1/week, and skipping off-season is fine.
- **Hooks:** "6 stocks pay you this week. The fattest: 8.4%, buy by Wednesday."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `8.4%` (teal) | C1 | "DIVIDEND WEEK · {n} STOCKS PAY" · "{T} pays Rp {x}/share · buy by {Wed 15 Oct}" |
| 2 | The list | top row | C6 (≤5) | "Last day to buy, ranked by yield" · note = buy by {date} |
| 3 | Plan the week | busiest day | C7 | "Your week" · "Ex-date is the next day; price usually drops ~the dividend" |
| 4 | Close | question | C8 | "Yield uses last close. Not advice." Q: "Which one are you holding into cum-date?" |

- **Skip when:**
  - fewer than 3 payers;
  - a row is missing a date, amount or close.
  - Drop S3 when all cum-dates fall on 1-2 days.
  - Don't hero a yield > 20% unless it is labelled "special".
  - Don't repeat last week's hero.
- **Risks:**
  - USD-denominated dividends (coal names), so check currency.
  - Cum vs ex confusion. The copy says "buy by {cum_date}".

### 8 · Weekly roundup
The only post with a fixed cadence. It replaces 4 posts with 1.

- **Replaces:**
  - `winners_losers.py` / `top_movers.py` (weekly_movers_social.yml)
  - `foreign_flow.py`
  - `sector_heatmap.py` (dropped)
  - the broker-weekly / accumulation / bandar modes in `broker_social.yml`
  - Retire their routing and queue entries so the same week isn't posted twice.
- **Data:**
  - `index_daily_data` IHSG (~260 rows for "worst since")
  - `idx_daily_data` (weekly return for top-100; foreign net for top-200)
  - `idx_broker_summary_daily` + `idx_broker_registry`
  - **New** wrapper `fetch_weekly_roundup()` over the existing fetchers
- **Trigger:** every Saturday for the Mon-Fri week. Skip if there were fewer than 3 trading days.
  - The cover is IHSG unless another hook score is > 2× larger. Hook score = max(|IHSG %|/1.5, |top mover|/15, |top foreign|/Rp 1 T, streak/4).
- **Hooks:** "IHSG lost 3.1% this week, its worst since March." · "Foreigners pulled Rp 2.4 T out of BBRI."

| # | Purpose | Focal point | Component | Text |
|---|---|---|---|---|
| 1 | Hook | `−3.1%` | C1 + C4 `spark` (5 closes) | "THIS WEEK ON IDX" · "IHSG closed at {x}, worst week since {m}" (only if computed) |
| 2 | Movers | #1 mover | C6 `diverging` (3 up / 3 down) | "Biggest movers (top-100 stocks)" |
| 3 | Foreign money | largest \|net\| | C6 `diverging` | "Foreign money this week (approx., top-200)" |
| 4 | Brokers *(rare)* | #1 broker | C6 | Only if #1 is NEW in the top 5 or rose 3+ ranks |
| 5 | Close | question | C8 | "Red week or buying week?" Q: "What are you holding into Monday?" |

- **Skip when:**
  - Drop S2's side if there's no mover ≥ 5%.
  - Drop S3 if all flows are < Rp 50 B.
  - Leave out corporate-action and ARA/ARB-no-volume names.
  - The same ticker never leads both S2 and S3.
- **Risks:**
  - Crossings inflate foreign flow.
  - The universe must be stated on the slide.
  - Broker pagination is slow. The broker slide is the first to drop.

---

## 4. Shared rules

| Rule | Detail |
|---|---|
| One focal point | Each slide has one thing that is biggest or brightest. Slide 1 must pass the 2-second "emak-emak" test: one number or one picture, no legend. |
| One accent | Teal = buy / up / money in. Rose = sell / down. Ownership uses the "hi" warm grey. Diverging lists colour **only the leading row** in its accent; the other side stays grey outline. |
| Slide count | 3-5, typically 4: hook → proof (chart or list) → context → close. A conditional slide is dropped, never padded. |
| Closing slide | Always C8: ≤3 facts plus a **neutral** question ("Why…?", "Would you…?", "What are you holding?"). |
| Numbers | Rupiah in words (`Rp 2.4 trillion`). Any approximation is labelled "approx." A "record" or "worst since" claim appears only when computed. Snapshot data says "as of {date}". |
| Honesty | Pre-arranged / nego / repo / mesop / rights prices are not "below market" (skip or show the stated purpose). Near-zero-base YoY is never shown as a %. Never imply wrongdoing about a named person. Never guess a counterparty or a person behind a holding vehicle. No buy/sell advice wording. |
| Object vs chart vs number | **Object (C2)** only for part-of-whole stakes (#1, #4). **Chart** only when the data is a trend over time (C4, C5) or a gap between two values (C3). **List** when there are names plus values. **Plain number** when one comparison says it all. If removing an element loses no meaning, remove it. |
| Objects | One drawing per sector, made once in `objects.js` and governed by `OBJECTS.md`. No per-post objects. |
| Dedupe | Each type has a state file. When types overlap: #1 beats #2. #3 and #5 never feature the same ticker in the same week. #8 owns weekly movers and flows. |

---

## 5. Build order

| Step | Build | Unlocks |
|---|---|---|
| 1 | **C1 NUMBER.hero** (extract), keep C6 + C8 as they are, `fmt.moneyWords` | the skeleton of every type |
| 2 | **C2 UNITS.field** (merge waffle + obj_bags_many; one object per sector, starting with the sectors in the first month's posts) | **#1 ship first** (`insider_move.py` pipeline + state already exist; strongest topic: person + Rp + ticker), then #4 |
| 3 | C3 label generalisation | #2 (and #1 slide 2) |
| 4 | C6 `diverging` + C4 `spark` + `fetch_weekly_roundup()` | **#8**, which retires 4 old workflows |
| 5 | C4 `window` / `refLine` + 5-year paginated fetch | #5, #3 S2 |
| 6 | **C5 CHART.bars** (history / pair / streak) + `fetch_drawdown_streak()` | #6 (time it for the next reporting season), #3 |
| 7 | C7 STRIP.week | #7 (before the Apr-Jul dividend season) |

Ship order: **#1 → #4 → #8 → #2 → #5 → #3 → #6 → #7.**
