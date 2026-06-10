"""Trigger layer — turns classified insider patterns into the two feeds.

Two feeds off ONE detection engine (see classification.group_insider_clusters /
group_insider_chains):

* SIGNAL (leading): a pattern caught *before* the market reacted. Fires the run
  it qualifies, gated on filing freshness, deduped so it posts once (re-fires
  only when it escalates — more holders / more filings). Makes no market claim.

* STORY (hindsight): the same pattern at 3/6/9-month checkpoints after its last
  filing. Gated on a >= 15% price move over the horizon. Copy is honest about
  whether the move validated the insiders (contradicting moves DO post).

Dedup state persists in a committed JSON file so repeated CI runs don't re-post:

    {"signals": {"<signal_key>": {...}},
     "stories": {"<signal_key>:<h>mo": {...}}}

The selectors are READ-ONLY (they filter against the state); call record_* +
save_state only after a post actually goes out, so a dry-run never burns a key.
"""
from __future__ import annotations

import json
from datetime import date, datetime
from pathlib import Path

SIGNAL_FRESHNESS_DAYS = 7          # a "fresh" completion: last filing within a week of the run
STORY_HORIZONS = (3, 6, 9)         # months after the last filing to look back from
STORY_MOVE_GATE = 0.15             # |move| must clear 15% for the story to be worth telling
# NOTE: bad-data filtering (netted mixed-leg / rights-issue filings, e.g. CYBR)
# is deferred. The proper fix is a mixed-buy+sell-leg detector applied to BOTH
# feeds — see idx-filings-data-quirks. A blunt filing_px/market ratio gate was
# tried and removed: it can't tell a legit big gap (GPSO 0.34x) from corrupt
# netting (CYBR 2.6x) since both sit far from market.

DEFAULT_STATE_PATH = Path("state/posted_insider.json")


# --------------------------------------------------------------------------- #
# State store (committed JSON)
# --------------------------------------------------------------------------- #
def load_state(path=DEFAULT_STATE_PATH):
    path = Path(path)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("signals", {})
            data.setdefault("stories", {})
            return data
        except (ValueError, OSError):
            pass
    return {"signals": {}, "stories": {}}


def save_state(state, path=DEFAULT_STATE_PATH):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(state, indent=2, sort_keys=True), encoding="utf-8")


# --------------------------------------------------------------------------- #
# Small date helpers
# --------------------------------------------------------------------------- #
def _parse_date(value):
    if isinstance(value, date) and not isinstance(value, datetime):
        return value
    if isinstance(value, datetime):
        return value.date()
    try:
        return datetime.strptime(str(value)[:10], "%Y-%m-%d").date()
    except (ValueError, TypeError):
        return None


def _add_months(d, months):
    """Calendar-add months, clamping the day to the target month's length."""
    idx = d.month - 1 + months
    year = d.year + idx // 12
    month = idx % 12 + 1
    last = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    if month == 2 and not (year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)):
        last = 28
    return date(year, month, min(d.day, last))


def _close_on_or_before(closes, target):
    """Latest close at or before `target` (dict of 'YYYY-MM-DD' -> float)."""
    if not closes:
        return None
    t = target.strftime("%Y-%m-%d") if hasattr(target, "strftime") else str(target)[:10]
    keys = sorted(k for k in closes if k <= t)
    return closes[keys[-1]] if keys else None


# --------------------------------------------------------------------------- #
# SIGNAL feed
# --------------------------------------------------------------------------- #
def select_signal_fires(patterns, run_date, state, freshness_days=SIGNAL_FRESHNESS_DAYS):
    """Fresh pattern completions not already posted (or that have escalated).

    Freshness routes stale backlog OUT of the signal feed and INTO the story
    feed automatically: an old cluster's last filing is > `freshness_days` ago,
    so it never qualifies here but does cross a story horizon.
    """
    run = _parse_date(run_date) or datetime.now().date()
    posted = state.get("signals", {})
    fires = []
    for p in patterns:
        completed = _parse_date(p.get("completed_date"))
        if completed is None or completed > run:
            continue
        if (run - completed).days > freshness_days:
            continue
        key = p.get("signal_key")
        if not key:
            continue
        count = p.get("progress_count") or 0
        prev = posted.get(key)
        if prev is None:
            p["_signal_update"] = False
            fires.append(p)
        elif count > (prev.get("progress_count") or 0):
            p["_signal_update"] = True   # more holders / filings since last post
            fires.append(p)
        # else: already posted at this size — skip (dedup)
    return fires


def record_signal(state, pattern, run_date):
    state.setdefault("signals", {})[pattern["signal_key"]] = {
        "progress_count": pattern.get("progress_count") or 0,
        "completing_filing_id": pattern.get("completing_filing_id"),
        "completed_date": pattern.get("completed_date"),
        "posted_at": str(_parse_date(run_date) or run_date),
    }


# --------------------------------------------------------------------------- #
# STORY feed
# --------------------------------------------------------------------------- #
def select_story_fires(patterns, run_date, state, price_fetcher, gate=STORY_MOVE_GATE):
    """Patterns that crossed a 3/6/9-month checkpoint with a >= `gate` move.

    `price_fetcher(symbol, completed_date)` -> {'YYYY-MM-DD': close}. For each
    pattern we tell at most ONE story per run: the strongest qualifying horizon
    crossed-but-not-yet-told. Every crossed horizon evaluated this run is marked
    told afterward (record_story), so weaker/under-gate duplicates never resurface
    (the move to a fixed past checkpoint can't change).
    """
    run = _parse_date(run_date) or datetime.now().date()
    told = state.get("stories", {})
    fires = []
    for p in patterns:
        completed = _parse_date(p.get("completed_date"))
        key = p.get("signal_key")
        if completed is None or not key:
            continue

        crossed = []
        for h in STORY_HORIZONS:
            checkpoint = _add_months(completed, h)
            if run < checkpoint:
                continue
            kh = f"{key}:{h}mo"
            if kh in told:
                continue
            crossed.append((h, checkpoint, kh))
        if not crossed:
            continue

        closes = price_fetcher(p["symbol"], completed) or {}
        start = _close_on_or_before(closes, completed)
        if not start:
            continue

        evaluated = []
        for h, checkpoint, kh in crossed:
            end = _close_on_or_before(closes, checkpoint)
            if end:
                evaluated.append((h, checkpoint, kh, (end - start) / start))
        if not evaluated:
            continue

        eligible = [e for e in evaluated if abs(e[3]) >= gate]
        chosen = max(eligible, key=lambda e: abs(e[3])) if eligible else None
        # all horizons looked at this run get retired regardless of outcome
        all_keys = [e[2] for e in evaluated]
        if chosen:
            h, checkpoint, kh, move = chosen
            direction = p.get("direction")
            validated = (direction == "buy" and move > 0) or (direction == "sell" and move < 0)
            sp = dict(p)
            sp["_story"] = {
                "horizon_months": h,
                "move": move,
                "validated": validated,
                "anchor_date": p.get("completed_date"),
                "checkpoint_date": checkpoint.strftime("%Y-%m-%d"),
                "fire_key": kh,
                "retire_keys": all_keys,
            }
            fires.append(sp)
        else:
            # nothing cleared the gate — retire the crossed horizons quietly
            p["_story_skip_keys"] = all_keys
    return fires


def record_story(state, pattern, run_date):
    """Retire every horizon evaluated for this pattern this run (told once)."""
    told = state.setdefault("stories", {})
    story = pattern.get("_story", {})
    stamp = str(_parse_date(run_date) or run_date)
    for k in story.get("retire_keys", []):
        told[k] = {"posted_at": stamp,
                   "move": round(story["move"], 4) if k == story.get("fire_key") else None}


def record_story_skips(state, patterns, run_date):
    """Retire crossed-but-under-gate (or price-insane) horizons so they aren't
    re-evaluated forever."""
    told = state.setdefault("stories", {})
    stamp = str(_parse_date(run_date) or run_date)
    for p in patterns:
        for k in p.get("_story_skip_keys", []) or []:
            told.setdefault(k, {"posted_at": stamp, "move": None, "skipped": True})


def retire_story(state, pattern, run_date):
    """Retire a story's horizons WITHOUT posting — used when a same-stock+direction
    carousel already posted this run, so this near-duplicate is superseded."""
    told = state.setdefault("stories", {})
    stamp = str(_parse_date(run_date) or run_date)
    for k in pattern.get("_story", {}).get("retire_keys", []):
        told.setdefault(k, {"posted_at": stamp, "move": None, "superseded": True})


# --------------------------------------------------------------------------- #
# BECOMING-INSIDER feed (standalone — its own state file, never mixed with the
# cluster/chain/cross signal feed). A 5% crossing is a leading, one-time event.
# --------------------------------------------------------------------------- #
BECOMING_STATE_PATH = Path("state/posted_becoming.json")
BECOMING_FRESHNESS_DAYS = 7


def load_becoming_state(path=BECOMING_STATE_PATH):
    path = Path(path)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("becoming", {})
            return data
        except (ValueError, OSError):
            pass
    return {"becoming": {}}


def select_becoming_fires(events, run_date, state, freshness_days=BECOMING_FRESHNESS_DAYS):
    """Fresh 5% crossings not already posted. A crossing is a one-time event, so
    there is no escalation — we re-fire only if a genuinely NEW crossing filing
    appears for the same holder+symbol (the rare drop-below-then-recross case)."""
    run = _parse_date(run_date) or datetime.now().date()
    posted = state.get("becoming", {})
    fires = []
    for e in events:
        crossed = _parse_date(e.get("cross_date"))
        if crossed is None or crossed > run:
            continue
        if (run - crossed).days > freshness_days:
            continue
        key = e.get("signal_key")
        if not key:
            continue
        prev = posted.get(key)
        if prev is None:
            fires.append(e)
        else:
            fid = e.get("completing_filing_id")
            if fid is not None and fid != prev.get("completing_filing_id"):
                fires.append(e)
    return fires


def record_becoming(state, event, run_date):
    state.setdefault("becoming", {})[event["signal_key"]] = {
        "completing_filing_id": event.get("completing_filing_id"),
        "cross_date": event.get("cross_date"),
        "posted_at": str(_parse_date(run_date) or run_date),
    }


# --------------------------------------------------------------------------- #
# EARNINGS feed (standalone). No report-publish date exists in idx_company_report,
# so freshness can't be gated on a timestamp. Instead: "new" = this
# (symbol, quarter, direction) is unposted, and a quarter-end recency gate keeps
# us on the CURRENT reporting season rather than re-surfacing an old back-catalog.
# --------------------------------------------------------------------------- #
EARNINGS_STATE_PATH = Path("state/posted_earnings.json")
EARNINGS_RECENCY_DAYS = 150


def load_earnings_state(path=EARNINGS_STATE_PATH):
    path = Path(path)
    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("earnings", {})
            return data
        except (ValueError, OSError):
            pass
    return {"earnings": {}}


def select_earnings_fires(spikes, run_date, state, recency_days=EARNINGS_RECENCY_DAYS):
    """Earnings spikes/drops for an unposted (symbol, quarter, direction), whose
    latest quarter ended within `recency_days` (so we report the live season, not
    a symbol stuck on an old quarter). Returns them as given — caller sorts/caps."""
    run = _parse_date(run_date) or datetime.now().date()
    posted = state.get("earnings", {})
    fires = []
    for s in spikes:
        key = s.get("signal_key")
        if not key or key in posted:
            continue
        qend = _parse_date(s.get("latest_quarter_date"))
        if qend is not None and (run - qend).days > recency_days:
            continue
        fires.append(s)
    return fires


def record_earnings(state, spike, run_date):
    state.setdefault("earnings", {})[spike["signal_key"]] = {
        "earnings_growth": spike.get("earnings_growth"),
        "latest_quarter": spike.get("latest_quarter"),
        "posted_at": str(_parse_date(run_date) or run_date),
    }
