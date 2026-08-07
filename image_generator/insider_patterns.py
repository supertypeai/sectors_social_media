"""Insider-filing pattern detection: clusters, chains, cross-stock, becoming-insider,
and report-led earnings spikes/drops.

Extracted from classification.py so the insider analysis layer lives in its own
module (keeps classification.py's diff small + conflict-free on merge). Depends
one-directionally on classification.py for a couple of shared tag helpers and
constants; nothing in classification imports back from here.
"""
import ast
import json
import re
from datetime import datetime, timedelta
from collections import Counter, defaultdict

import pandas as pd

from .classification import (
    parse_tags,
    add_parsed_tags,
    EXCLUDED_PLAIN_FILINGS_TAGS,
    IMPORTANT_FILINGS_TAGS,
    MAX_SANE_PRICE,
)


def parse_price_transactions(value):
    """Normalize a filing's price_transaction into a list of dicts.

    Supabase returns it already parsed (list of dicts); CSV/JSONL may give a string.
    """
    if isinstance(value, list):
        return [entry for entry in value if isinstance(entry, dict)]
    if value is None:
        return []
    if isinstance(value, float) and pd.isna(value):
        return []
    text = str(value).strip()
    if not text or text.lower() in {"nan", "none", "null", "[]"}:
        return []
    for parser in (json.loads, ast.literal_eval):
        try:
            parsed = parser(text)
            if isinstance(parsed, list):
                return [entry for entry in parsed if isinstance(entry, dict)]
        except Exception:
            pass
    return []


def _has_mixed_legs(row):
    """True if a filing's price_transaction carries BOTH buy and sell legs.

    That's the netting signature of a compiled/mixed filing whose filing-level
    amount_transaction / transaction_value / price are netted garbage (see the
    idx_filings data quirks: e.g. CYBR). Each leg has a 'type' of 'buy'/'sell'.
    """
    types = {
        str(leg.get("type", "")).strip().lower()
        for leg in parse_price_transactions(row.get("price_transaction"))
    }
    return "buy" in types and "sell" in types


def drop_mixed_leg_filings(df):
    """Drop netted mixed-leg filings so corrupt data never reaches either feed.

    Applied once at the signal/story entry point; targets ~2% of rows (the
    actual buy+sell-in-one-filing bug) without touching clean single-direction
    filings — the precise alternative to a filing-price sanity gate.
    """
    if df is None or df.empty or "price_transaction" not in df.columns:
        return df
    return df[~df.apply(_has_mixed_legs, axis=1)]


def _is_empty(value):
    if value is None:
        return True
    if isinstance(value, (list, dict)):
        return len(value) == 0
    if pd.isna(value):
        return True
    text = str(value).strip()
    return text == "" or text.lower() in {"nan", "none", "null", "nat", "[]"}


def filter_plain_filings(
    df,
    now=None,
):
    """Plain insider-trading filings from the PREVIOUS WIB day: insider buy/sell,
    no context, not MESOP/takeover.

    Keyed on `timestamp` (the actual filing event, stored naive in WIB) over a
    full previous-calendar-day window — NOT `created_at`/scrape-time. This feed
    is meant to run in the morning and show a COMPLETE picture of *yesterday*:
    only ~67% of a day's filings are scraped by 20:00 the same day (filings run
    well into the evening, scrape lag ~2-4h), so a same-night "today" window
    would silently miss ~1/3 of them. By the next morning, yesterday's evening
    filings have been scraped overnight, so "yesterday" is complete.

    `now` is the run moment (defaults to WIB now); the window is the WIB calendar
    day immediately before it. The `highlights` column is not part of this
    filter — confirmed not applicable.
    """
    df = add_parsed_tags(df)
    if df.empty:
        return df

    # Filing event time is stored naive, already in WIB.
    filing_ts = pd.to_datetime(df["timestamp"], errors="coerce")

    # "Yesterday" in WIB relative to the run moment.
    if now is None:
        now = pd.Timestamp.now(tz="Asia/Jakarta")
    now = pd.Timestamp(now)
    if now.tzinfo is not None:
        now = now.tz_convert("Asia/Jakarta").tz_localize(None)
    target_day = (now - pd.Timedelta(days=1)).date()
    on_target_day = filing_ts.dt.date == target_day

    context_empty = (
        df["context"].apply(_is_empty)
        if "context" in df.columns
        else pd.Series(True, index=df.index)
    )
    insider = (
        df["holder_type"].apply(lambda v: str(v).strip().lower() == "insider")
        if "holder_type" in df.columns
        else pd.Series(True, index=df.index)
    )
    trading = (
        df["transaction_type"].apply(lambda v: str(v).strip().lower() in {"buy", "sell"})
        if "transaction_type" in df.columns
        else pd.Series(True, index=df.index)
    )
    not_mesop_takeover = df["tags_parsed"].apply(
        lambda tags: not ({str(tag).lower() for tag in tags} & EXCLUDED_PLAIN_FILINGS_TAGS)
    )

    plain_filings = df[
        on_target_day
        & context_empty
        & insider
        & trading
        & not_mesop_takeover
    ].copy()

    # One filing can be ingested more than once with different record IDs
    card_fields = [
        "symbol",
        "holder_name",
        "transaction_type",
        "transaction_value",
        "amount_transaction",
        "price",
        "share_percentage_before",
        "share_percentage_after",
    ]

    return plain_filings.sort_values(
        "transaction_value", ascending=False
    ).drop_duplicates(
        subset=card_fields,
        keep="first",
    )


def _safe_float(value):
    try:
        f = float(value)
    except (TypeError, ValueError):
        return None
    return None if f != f else f  # drop NaN


def _normalize_holder_key(name):
    """Collapse casing + word-order variants so 'Suresh Vembu' == 'Vembu Suresh'."""
    return " ".join(sorted(str(name or "").strip().lower().split()))


def _subtract_months(d, months):
    month = d.month - months
    year = d.year
    while month <= 0:
        month += 12
        year -= 1
    last_day = [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31][month - 1]
    return d.replace(year=year, month=month, day=min(d.day, last_day))


def _filing_date(row):
    from datetime import datetime

    for col in ("timestamp", "created_at"):
        raw = row.get(col)
        if raw is None or (isinstance(raw, float) and pd.isna(raw)):
            continue
        try:
            return datetime.fromisoformat(str(raw).replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            continue
    return None


def _filing_legs(row):
    """Yield (date, price, shares) legs for one filing, guarded against bad prices.

    Prefers the per-trade price_transaction breakdown; falls back to the
    filing-level columns when the breakdown is missing/unusable.
    """
    legs = []
    for entry in parse_price_transactions(row.get("price_transaction")):
        price = _safe_float(entry.get("price"))
        shares = _safe_float(entry.get("amount_transacted") or entry.get("amount"))
        date = str(entry.get("date") or "")[:10]
        if not date or price is None or shares is None:
            continue
        if price <= 0 or price > MAX_SANE_PRICE or shares <= 0:
            continue
        legs.append((date, price, shares))
    if legs:
        return legs

    # Fallback: single filing-level leg.
    fdate = _filing_date(row)
    date = fdate.strftime("%Y-%m-%d") if fdate else None
    price = _safe_float(row.get("price"))
    shares = _safe_float(row.get("amount_transaction"))
    if date and price and shares and 0 < price <= MAX_SANE_PRICE and shares > 0:
        return [(date, price, shares)]
    return []


def _filing_totals(row):
    """One (date, avg_price, shares, value) tuple per filing, dated on the record date.

    Uses the authoritative filing-level columns; falls back to the per-trade
    breakdown when those are missing or fail the price sanity guard.
    """
    fdate = _filing_date(row)
    if fdate is None:
        return None
    date = fdate.strftime("%Y-%m-%d")
    shares = _safe_float(row.get("amount_transaction"))
    value = _safe_float(row.get("transaction_value"))
    if shares and shares > 0 and value and value > 0 and 0 < value / shares <= MAX_SANE_PRICE:
        return (date, value / shares, shares, value)

    legs = _filing_legs(row)
    if legs:
        tot_sh = sum(s for _, _, s in legs)
        tot_val = sum(p * s for _, p, s in legs)
        if tot_sh > 0:
            return (date, tot_val / tot_sh, tot_sh, tot_val)

    price = _safe_float(row.get("price"))
    if price and 0 < price <= MAX_SANE_PRICE and shares and shares > 0:
        return (date, price, shares, price * shares)
    return None


def _filing_price_point(row):
    """One (date, price, shares, value) per filing, PRICE-COLUMN first.

    Evelyn's call for the cluster chart: use the filing-level `price` column (the
    disclosed weighted/net-settlement price) rather than re-deriving from the
    per-leg price_transaction breakdown. value is price*shares so that any
    per-insider weighted average (value/shares) stays internally consistent — the
    chart dot then sits exactly on the roster's AVG line. Falls back to
    _filing_totals when the price column is missing or fails the sanity guard.
    """
    fdate = _filing_date(row)
    if fdate is None:
        return None
    date = fdate.strftime("%Y-%m-%d")
    price = _safe_float(row.get("price"))
    shares = _safe_float(row.get("amount_transaction"))
    if price and 0 < price <= MAX_SANE_PRICE and shares and shares > 0:
        return (date, price, shares, price * shares)
    return _filing_totals(row)


def _max_insiders_within_days(rows):
    """Largest "N insiders filed ... within D days" figure across filings' highlights.

    The upstream pipeline writes these into idx_filings.highlights as a cluster
    builds; the max captures how concentrated the buying was in time (a tighter,
    punchier conviction stat than the 6-month detection window).
    """
    import re

    best_n, best_d = 0, None
    for row in rows:
        for item in parse_tags(row.get("highlights")):
            m = re.search(r"(\d+)\s+insiders?\s+filed.*?within\s+(\d+)\s+day", str(item), re.I)
            if m and int(m.group(1)) > best_n:
                best_n, best_d = int(m.group(1)), int(m.group(2))
    return (best_n, best_d) if best_n else (None, None)


def group_insider_clusters(df, min_holders=3, window_months=6):
    """Symbols where >= `min_holders` distinct insiders traded the same direction
    inside a trailing `window_months` window (anchored on the latest filing).

    Insiders only (holder_type == 'insider') and context-bearing filings only.
    Returns one render-ready dict per (symbol, direction), sorted by combined
    value descending.
    """
    from collections import Counter, defaultdict

    if df.empty or "holder_name" not in df.columns or "symbol" not in df.columns or "context" not in df.columns:
        return []

    df = add_parsed_tags(df)
    if "holder_type" in df.columns:
        df = df[df["holder_type"].apply(lambda v: str(v).strip().lower() == "insider")]
    df = df[df.get("transaction_type").apply(lambda v: str(v).strip().lower() in {"buy", "sell"})]
    df = df[df["context"].apply(lambda v: not _is_empty(v))]
    # MESOP/takeover-tagged filings get their own card types.
    df = df[df["tags_parsed"].apply(
        lambda tags: not ({str(tag).lower() for tag in tags} & IMPORTANT_FILINGS_TAGS)
    )]
    if df.empty:
        return []

    # Flatten to records with a resolved filing date + normalized holder key.
    records = []
    raw_by_key = defaultdict(Counter)
    for row in df.to_dict("records"):
        d = _filing_date(row)
        if d is None or not row.get("symbol") or not row.get("holder_name"):
            continue
        key = _normalize_holder_key(row["holder_name"])
        raw_by_key[key][row["holder_name"]] += 1
        records.append({**row, "_date": d, "_hkey": key, "_dir": str(row["transaction_type"]).strip().lower()})
    display_name = {k: c.most_common(1)[0][0] for k, c in raw_by_key.items()}

    groups = defaultdict(list)
    for r in records:
        groups[(r["symbol"], r["_dir"])].append(r)

    clusters = []
    for (symbol, direction), recs in groups.items():
        recs.sort(key=lambda r: r["_date"])
        anchor = recs[-1]["_date"]
        lo = _subtract_months(anchor, window_months)
        lo_d, hi_d = lo.date(), anchor.date()  # window is date-level, per the brief
        in_win = [r for r in recs if lo_d <= r["_date"].date() <= hi_d]
        holder_keys = {r["_hkey"] for r in in_win}
        if len(holder_keys) < min_holders:
            continue

        from datetime import datetime as _dt

        roster = {k: {"shares": 0.0, "value": 0.0, "filings": 0, "first": None,
                      "last": None, "ownership_after": None} for k in holder_keys}
        # One dot per (insider, real filing date): same-day filings collapse to a
        # single VWAP dot (legit — they're lot-splits of one event), while filings
        # on different dates each keep their own dot. Every dot lands on a real date
        # and real price, so the chart shows true cadence (replaces the old
        # share-weighted single-dot-per-insider collapse).
        by_key_date = defaultdict(lambda: {"shares": 0.0, "value": 0.0})
        filing_count = 0
        all_dates = []
        for r in in_win:
            agg = roster[r["_hkey"]]
            agg["filings"] += 1
            after = r.get("share_percentage_after")
            if after is not None and not (isinstance(after, float) and pd.isna(after)):
                agg["ownership_after"] = after  # latest wins (recs sorted ascending)
            tot = _filing_price_point(r)
            if tot is None:
                continue
            date, price, shares, value = tot
            filing_count += 1
            all_dates.append(date)
            agg["shares"] += shares
            agg["value"] += value
            agg["first"] = date if agg["first"] is None else min(agg["first"], date)
            agg["last"] = date if agg["last"] is None else max(agg["last"], date)
            g = by_key_date[(r["_hkey"], date)]
            g["shares"] += shares
            g["value"] += value

        points = []
        for (k, date), g in by_key_date.items():
            if g["shares"] <= 0 or g["value"] <= 0:
                continue
            points.append({"date": date, "price": g["value"] / g["shares"],
                           "shares": g["shares"], "hkey": k})

        roster_list = sorted(
            (
                {
                    "key": k,
                    "name": display_name.get(k, k.title()),
                    "shares": v["shares"],
                    "value": v["value"],
                    "filings": v["filings"],
                    "first_date": v["first"],
                    "last_date": v["last"],
                    "ownership_after": v["ownership_after"],
                }
                for k, v in roster.items()
            ),
            key=lambda h: h["value"],
            reverse=True,
        )

        # Filing-period label = the real filing dates (not the weighted dot dates).
        first_date = min(all_dates) if all_dates else lo.strftime("%Y-%m-%d")
        last_date = max(all_dates) if all_dates else anchor.strftime("%Y-%m-%d")
        months = None
        try:
            months = max(1, round((_dt.strptime(last_date, "%Y-%m-%d") - _dt.strptime(first_date, "%Y-%m-%d")).days / 30))
        except ValueError:
            pass

        sample_context = next(
            (r.get("context") for r in reversed(in_win)
             if isinstance(r.get("context"), str) and "insider" in r["context"].lower()),
            None,
        )
        filed_n, filed_d = _max_insiders_within_days(in_win)

        bsym = str(symbol).upper().split(".")[0]
        clusters.append(
            {
                "symbol": symbol,
                "base_symbol": bsym,
                "direction": direction,
                "pattern": "Cluster Buy" if direction == "buy" else "Cluster Sell",
                "holder_count": len(holder_keys),
                "filing_count": filing_count,
                # --- trigger-layer firing metadata (signal/story feeds) ---
                "kind": "cluster",
                "signal_key": f"cluster:{bsym}:{direction}",
                "progress_count": len(holder_keys),
                "completed_date": anchor.strftime("%Y-%m-%d"),
                "completing_filing_id": recs[-1].get("id"),
                "roster": roster_list,
                "points": points,
                "total_shares": sum(h["shares"] for h in roster_list),
                "total_value": sum(h["value"] for h in roster_list),
                "first_date": first_date,
                "last_date": last_date,
                "window_start": lo.strftime("%Y-%m-%d"),
                "window_end": anchor.strftime("%Y-%m-%d"),
                "months": months,
                "context": sample_context,
                "filed_within": filed_n,
                "filed_within_days": filed_d,
            }
        )

    return sorted(clusters, key=lambda c: c["total_value"], reverse=True)


def _chain_forward_return(rows):
    """Most recent forward-return backtest from highlights, signed by direction.

    "Insider buy in CYBR historically gained 25.7% (median: 26.9%) within 60 days."
    -> {"mean": 25.7, "median": 26.9, "days": 60}  (declines come back negative)
    """
    best = None
    for row in rows:
        for item in parse_tags(row.get("highlights")):
            m = re.search(
                r"historically\s+(gained|declined)\s+([\d.]+)%.*?median:\s*(-?[\d.]+)%.*?within\s+(\d+)\s+day",
                str(item), re.I)
            if m:
                sign = 1 if m.group(1).lower() == "gained" else -1
                best = {"mean": sign * float(m.group(2)), "median": float(m.group(3)), "days": int(m.group(4))}
    return best


def _chain_size_anomaly(rows):
    """Largest "Nx typical buy/sell size … at Rp X" multiple from highlights."""
    best_mult, best = 0.0, None
    for row in rows:
        for item in parse_tags(row.get("highlights")):
            m = re.search(r"([\d.]+)x\s+typical\s+(buy|sell)\s+size.*?at\s+Rp\s+([\d.,]+\s*[TBMK]?)", str(item), re.I)
            if m and float(m.group(1)) > best_mult:
                best_mult = float(m.group(1))
                best = {"mult": float(m.group(1)), "side": m.group(2).lower(), "at": m.group(3).strip()}
    return best


def group_insider_chains(df, min_filings=3, window_months=6, min_value=1_000_000_000):
    """Insiders who traded the SAME symbol+direction `min_filings`+ times inside a
    trailing `window_months` window (anchored on their latest filing).

    Insiders only, context-bearing filings only, MESOP/takeover excluded (same
    gates as group_insider_clusters). Returns one render-ready dict per
    (holder, symbol, direction), sorted by combined value descending.
    """
    from collections import Counter, defaultdict
    from datetime import datetime as _dt

    if df.empty or not {"holder_name", "symbol", "context"} <= set(df.columns):
        return []

    df = add_parsed_tags(df)
    if "holder_type" in df.columns:
        df = df[df["holder_type"].apply(lambda v: str(v).strip().lower() == "insider")]
    df = df[df.get("transaction_type").apply(lambda v: str(v).strip().lower() in {"buy", "sell"})]
    df = df[df["context"].apply(lambda v: not _is_empty(v))]
    df = df[df["tags_parsed"].apply(
        lambda tags: not ({str(t).lower() for t in tags} & IMPORTANT_FILINGS_TAGS))]
    if df.empty:
        return []

    records = []
    raw_by_key = defaultdict(Counter)
    for row in df.to_dict("records"):
        d = _filing_date(row)
        if d is None or not row.get("symbol") or not row.get("holder_name"):
            continue
        key = _normalize_holder_key(row["holder_name"])
        raw_by_key[key][row["holder_name"]] += 1
        records.append({**row, "_date": d, "_hkey": key, "_dir": str(row["transaction_type"]).strip().lower()})
    display_name = {k: c.most_common(1)[0][0] for k, c in raw_by_key.items()}

    groups = defaultdict(list)
    for r in records:
        groups[(r["_hkey"], r["symbol"], r["_dir"])].append(r)

    chains = []
    for (hkey, symbol, direction), recs in groups.items():
        recs.sort(key=lambda r: r["_date"])
        anchor = recs[-1]["_date"]
        lo = _subtract_months(anchor, window_months)
        in_win = [r for r in recs if lo.date() <= r["_date"].date() <= anchor.date()]
        if len(in_win) < min_filings:
            continue

        points, ownership = [], []
        own_first = own_last = None
        for r in in_win:
            tot = _filing_price_point(r)  # price column first, same source as the cluster chart
            if tot:
                date, price, shares, value = tot
                points.append({"date": date, "price": price, "shares": shares, "value": value, "hkey": hkey})
            b = _safe_float(r.get("share_percentage_before"))
            a = _safe_float(r.get("share_percentage_after"))
            if own_first is None and b is not None:
                own_first = b
            if a is not None:
                ownership.append({"date": r["_date"].strftime("%Y-%m-%d"), "pct": a})
                own_last = a
        if not points:
            continue

        total_shares = sum(p["shares"] for p in points)
        total_value = sum(p["value"] for p in points)
        if total_value < min_value:
            continue
        avg_price = (total_value / total_shares) if total_shares else None
        dates = [p["date"] for p in points]
        first_date, last_date = min(dates), max(dates)
        months = None
        try:
            months = max(1, round((_dt.strptime(last_date, "%Y-%m-%d") - _dt.strptime(first_date, "%Y-%m-%d")).days / 30))
        except ValueError:
            pass

        bsym = str(symbol).upper().split(".")[0]
        chains.append(
            {
                "symbol": symbol,
                "base_symbol": bsym,
                "holder_name": display_name.get(hkey, hkey.title()),
                "direction": direction,
                "pattern": "Insider Chain Buy" if direction == "buy" else "Insider Chain Sell",
                "filing_count": len(points),
                # --- trigger-layer firing metadata (signal/story feeds) ---
                "kind": "chain",
                "signal_key": f"chain:{hkey}:{bsym}:{direction}",
                "progress_count": len(points),
                "completed_date": anchor.strftime("%Y-%m-%d"),
                "completing_filing_id": recs[-1].get("id"),
                "points": points,
                "ownership": ownership,
                "ownership_first": own_first,
                "ownership_last": own_last,
                "total_shares": total_shares,
                "total_value": total_value,
                "avg_price": avg_price,
                "first_date": first_date,
                "last_date": last_date,
                "window_start": lo.strftime("%Y-%m-%d"),
                "window_end": anchor.strftime("%Y-%m-%d"),
                "months": months,
                "context": in_win[-1].get("context"),
                "forward_return": _chain_forward_return(in_win),
                "size_anomaly": _chain_size_anomaly(in_win),
            }
        )

    return sorted(chains, key=lambda c: c["total_value"], reverse=True)


def group_becoming_insider(df, window_months=6, min_jump=0.02, min_value=500_000_000):
    """Holders who crossed 5% ownership upward inside a trailing window.

    A becoming-insider event = a buy filing where share_percentage_before < 5
    and share_percentage_after >= 5 (the crossing). Returns one render-ready
    dict per (holder, symbol) crossing, with the accumulation path of all their
    buys leading up to and including the crossing, sorted by stake-now desc.

    min_jump filters out razor-thin technical crossings (e.g. 4.99 -> 5.01) so
    the post always reflects a real conviction move; raise it for a stricter cut.
    """
    from collections import Counter, defaultdict
    from datetime import datetime as _dt

    needed = {"holder_name", "symbol", "share_percentage_before", "share_percentage_after"}
    if df.empty or not needed <= set(df.columns):
        return []

    df = add_parsed_tags(df)
    # Crossing applies to any substantial holder type (insider or institution),
    # but we keep the MESOP/takeover exclusion so it's a genuine market purchase.
    df = df[df.get("transaction_type").apply(lambda v: str(v).strip().lower() in {"buy", "others"})]
    df = df[df["tags_parsed"].apply(
        lambda tags: not ({str(t).lower() for t in tags} & IMPORTANT_FILINGS_TAGS))]
    if df.empty:
        return []

    records = []
    raw_by_key = defaultdict(Counter)
    for row in df.to_dict("records"):
        d = _filing_date(row)
        if d is None or not row.get("symbol") or not row.get("holder_name"):
            continue
        key = _normalize_holder_key(row["holder_name"])
        raw_by_key[key][row["holder_name"]] += 1
        records.append({**row, "_date": d, "_hkey": key})
    display_name = {k: c.most_common(1)[0][0] for k, c in raw_by_key.items()}

    groups = defaultdict(list)
    for r in records:
        groups[(r["_hkey"], r["symbol"])].append(r)

    events = []
    for (hkey, symbol), recs in groups.items():
        recs.sort(key=lambda r: r["_date"])
        anchor = recs[-1]["_date"]
        lo = _subtract_months(anchor, window_months)
        in_win = [r for r in recs if lo.date() <= r["_date"].date() <= anchor.date()]
        if not in_win:
            continue

        # Find the crossing: before < 5 <= after, picking the most recent one.
        crossing = None
        for r in in_win:
            b = _safe_float(r.get("share_percentage_before"))
            a = _safe_float(r.get("share_percentage_after"))
            if b is not None and a is not None and b < 5 <= a:
                crossing = r
        if crossing is None:
            continue

        cb = _safe_float(crossing.get("share_percentage_before")) or 0.0
        ca = _safe_float(crossing.get("share_percentage_after")) or 0.0
        if (ca - cb) < min_jump:  # razor-thin technical crossing — skip
            continue

        # Accumulation path: every buy up to and including the crossing date.
        points, traj = [], []
        for r in in_win:
            if r["_date"] > crossing["_date"]:
                continue
            tot = _filing_price_point(r)
            if tot:
                date, price, shares, value = tot
                points.append({"date": date, "price": price, "shares": shares, "value": value})
            a = _safe_float(r.get("share_percentage_after"))
            if a is not None:
                traj.append({"date": r["_date"].strftime("%Y-%m-%d"), "pct": a})
        if not points:
            continue
        traj.sort(key=lambda p: p["date"])

        total_shares = sum(p["shares"] for p in points)
        total_value = sum(p["value"] for p in points)
        if total_value < min_value:
            continue
        avg_price = (total_value / total_shares) if total_shares else None
        cross_tot = _filing_price_point(crossing)
        dates = [p["date"] for p in points]
        first_date = min(dates)
        cross_date = crossing["_date"].strftime("%Y-%m-%d")
        months = None
        try:
            months = max(1, round((_dt.strptime(cross_date, "%Y-%m-%d")
                                   - _dt.strptime(first_date, "%Y-%m-%d")).days / 30))
        except ValueError:
            pass

        is_inst = str(crossing.get("holder_type") or "").strip().lower() == "institution"
        base_symbol = str(symbol).upper().split(".")[0]
        events.append(
            {
                "symbol": symbol,
                "base_symbol": base_symbol,
                "holder_name": display_name.get(hkey, hkey.title()),
                # Trigger fields for the standalone becoming-insider feed. A 5%
                # crossing is a ONE-TIME event (no escalation) — dedupe on
                # holder+symbol, store the crossing filing id so a genuinely new
                # crossing (drop-below-then-recross) can re-fire.
                "signal_key": f"becoming:{hkey}:{base_symbol}",
                "completing_filing_id": crossing.get("id"),
                "holder_type": "institution" if is_inst else "insider",
                "pattern": "Becoming Insider",
                "stake_before": cb,
                "stake_after": ca,
                "stake_jump": ca - cb,
                "cross_date": cross_date,
                "cross_shares": _safe_float(crossing.get("amount_transaction")),
                "cross_value": _safe_float(crossing.get("transaction_value"))
                or (cross_tot[3] if cross_tot else None),
                "cross_price": cross_tot[1] if cross_tot else _safe_float(crossing.get("price")),
                "filing_count": len(points),
                "points": points,
                "trajectory": traj,
                "total_shares": total_shares,
                "total_value": total_value,
                "avg_price": avg_price,
                "first_date": first_date,
                "last_date": cross_date,
                "months": months,
            }
        )

    # Recency first — a daily automation wants the freshest crossing; tie-break on stake.
    return sorted(events, key=lambda e: (e["cross_date"], e["stake_after"]), reverse=True)


def select_earnings_spikes(df, direction="spike", min_growth=0.60, max_growth=8.0,
                           min_drop=0.40, max_drop=1.0, max_rank=150,
                           require_revenue=None, max_quarters=6, min_base_ratio=0.10):
    """Symbols whose latest-quarter earnings moved sharply YoY, report-led (no news join).

    direction="spike" keeps profit JUMPS (growth in [min_growth, max_growth]); the
    floor is 60% per the team's symmetric ±10-around-50 rule. direction="drop" keeps
    profit FALLS (growth in [-max_drop, -min_drop], i.e. down 40%+ but still profitable
    so we never measure a fall off a loss base). One renderer covers both cases — the
    sign of the growth drives the red/green styling.

    Gate: market_cap_rank <= max_rank and (when require_revenue) revenue also up,
    so the spike is broad-based rather than a one-off/margin artifact. For drops we
    don't require revenue to move in any direction (default require_revenue=False);
    revenue is still shown so viewers can see whether the fall is broad-based.

    Credibility guard — the headline % is recomputed from the SAME quarters shown
    in the chart (latest quarter vs the year-ago quarter, 4 positions back) rather
    than trusting the stored field, which blows up to absurd values (e.g.
    +1,284,231,324%) when the year-ago base is near zero. We require:
      - a positive year-ago base whose magnitude is >= min_base_ratio of the
        latest quarter (rejects near-zero-base / loss-to-profit turnarounds that
        produce fake-looking thousands-of-percent), and
      - min_growth <= growth <= max_growth (a believable spike band).
    When fewer than 5 quarters are available we fall back to the stored field but
    still apply the max_growth ceiling. Sorted by growth descending.
    """
    if df is None or df.empty:
        return []

    is_drop = direction == "drop"
    if require_revenue is None:
        require_revenue = not is_drop  # spikes must be broad-based; drops needn't be.

    def _quarter_key(label):
        # "Q1-2026" -> (2026, 1) for chronological sorting.
        try:
            q, y = str(label).split("-")
            return (int(y), int(q.lstrip("Qq")))
        except (ValueError, AttributeError):
            return (0, 0)

    spikes = []
    for row in df.to_dict("records"):
        g = _safe_float(row.get("yoy_quarter_earnings_growth"))
        rg = _safe_float(row.get("yoy_quarter_revenue_growth"))
        rank = _safe_float(row.get("market_cap_rank"))
        if rank is not None and rank > max_rank:
            continue

        hfq = row.get("historical_financials_quarterly")
        if isinstance(hfq, str):
            try:
                hfq = json.loads(hfq)
            except (ValueError, TypeError):
                hfq = None
        quarters = []
        if isinstance(hfq, dict):
            for label in sorted(hfq.keys(), key=_quarter_key):
                blk = hfq[label] or {}
                earnings = _safe_float(blk.get("earnings"))
                revenue = _safe_float(blk.get("revenue"))
                if earnings is None and revenue is None:
                    continue
                quarters.append({"label": label, "earnings": earnings, "revenue": revenue,
                                 "date": blk.get("date")})
            quarters = quarters[-max_quarters:]
        if len(quarters) < 2:
            continue

        # Recompute YoY from the same quarters shown in the chart when possible.
        rev_growth = rg
        if len(quarters) >= 5:
            base_e = quarters[-5].get("earnings")
            late_e = quarters[-1].get("earnings")
            base_r = quarters[-5].get("revenue")
            late_r = quarters[-1].get("revenue")
            # Reject loss-to-profit / near-zero-base artifacts.
            if base_e is None or late_e is None or base_e <= 0:
                continue
            if abs(base_e) < min_base_ratio * abs(late_e):
                continue
            g = (late_e - base_e) / base_e
            if base_r and late_r and base_r > 0:
                rev_growth = (late_r - base_r) / base_r
        else:
            # Fallback to the stored field; still drop absurd values.
            if g is None:
                continue

        if g is None:
            continue
        if is_drop:
            # A fall of >=40% but capped so we never report a fall off a loss base
            # (g <= -max_drop would mean profit went to ~zero or negative).
            if g > -min_drop or g < -max_drop:
                continue
        else:
            if g < min_growth or g > max_growth:
                continue
        if require_revenue and (rev_growth is None or rev_growth <= 0):
            continue

        hist_eps = row.get("historical_eps")
        if isinstance(hist_eps, str):
            try:
                hist_eps = json.loads(hist_eps)
            except (ValueError, TypeError):
                hist_eps = None
        eps_path = []
        if isinstance(hist_eps, dict):
            for yr in sorted(hist_eps.keys()):
                blk = hist_eps[yr] or {}
                eps_path.append({"year": yr, "eps": _safe_float(blk.get("eps")),
                                 "growth": _safe_float(blk.get("eps_growth"))})

        latest_q = quarters[-1]
        base_symbol = str(row.get("symbol")).upper().split(".")[0]
        spikes.append(
            {
                "symbol": row.get("symbol"),
                "base_symbol": base_symbol,
                # Trigger fields for the standalone earnings feed. No report-publish
                # date exists, so "new" = this (symbol, quarter, direction) triple
                # is unposted; latest_quarter_date (quarter-end) drives the recency
                # gate that keeps us on the current reporting season.
                "direction": direction,
                "signal_key": f"earnings:{base_symbol}:{latest_q['label']}:{direction}",
                "latest_quarter_date": latest_q.get("date"),
                "company_name": row.get("company_name"),
                "sector": row.get("sector"),
                "sub_sector": row.get("sub_sector"),
                "market_cap_rank": int(rank) if rank is not None else None,
                "earnings_growth": g,
                "revenue_growth": rev_growth,
                "eps": _safe_float(row.get("eps")),
                "forward_pe": _safe_float(row.get("forward_pe")),
                "last_close_price": _safe_float(row.get("last_close_price")),
                "daily_close_change": _safe_float(row.get("daily_close_change")),
                "quarters": quarters,
                "latest_quarter": latest_q["label"],
                "latest_earnings": latest_q["earnings"],
                "eps_path": eps_path,
            }
        )

    # Spikes: biggest jump first. Drops: biggest fall (most negative) first.
    return sorted(spikes, key=lambda s: s["earnings_growth"], reverse=not is_drop)


def group_insider_cross(df, min_symbols=2, window_months=6, min_value=1_000_000_000):
    """Insiders active across `min_symbols`+ distinct symbols in a trailing window.

    Same gates as group_insider_clusters/chains (insider-only, buy/sell,
    context-bearing, MESOP/takeover excluded). Returns one dict per holder with
    a per-symbol basket, sorted by combined value descending.
    """
    from collections import Counter, defaultdict

    if df.empty or not {"holder_name", "symbol", "context"} <= set(df.columns):
        return []

    df = add_parsed_tags(df)
    if "holder_type" in df.columns:
        df = df[df["holder_type"].apply(lambda v: str(v).strip().lower() == "insider")]
    df = df[df.get("transaction_type").apply(lambda v: str(v).strip().lower() in {"buy", "sell"})]
    df = df[df["context"].apply(lambda v: not _is_empty(v))]
    df = df[df["tags_parsed"].apply(
        lambda tags: not ({str(t).lower() for t in tags} & IMPORTANT_FILINGS_TAGS))]
    if df.empty:
        return []

    records = []
    raw_by_key = defaultdict(Counter)
    for row in df.to_dict("records"):
        d = _filing_date(row)
        if d is None or not row.get("symbol") or not row.get("holder_name"):
            continue
        key = _normalize_holder_key(row["holder_name"])
        raw_by_key[key][row["holder_name"]] += 1
        records.append({**row, "_date": d, "_hkey": key, "_dir": str(row["transaction_type"]).strip().lower()})
    display_name = {k: c.most_common(1)[0][0] for k, c in raw_by_key.items()}

    by_holder = defaultdict(list)
    for r in records:
        by_holder[r["_hkey"]].append(r)

    crosses = []
    for hkey, recs in by_holder.items():
        recs.sort(key=lambda r: r["_date"])
        anchor = recs[-1]["_date"]
        lo = _subtract_months(anchor, window_months)
        in_win = [r for r in recs if lo.date() <= r["_date"].date() <= anchor.date()]
        symbols = {r["symbol"] for r in in_win}
        if len(symbols) < min_symbols:
            continue

        per_sym = {}
        for r in in_win:
            sym = r["symbol"]
            s = per_sym.setdefault(sym, {
                "dirs": Counter(),
                "filings": 0,
                "shares": 0.0,
                "value": 0.0,
                "buy_value": 0.0,
                "sell_value": 0.0,
                "buy_filings": 0,
                "sell_filings": 0,
                "points": [],
                "first": None,
                "last": None,
                "own": None,
            })
            s["dirs"][r["_dir"]] += 1
            s["filings"] += 1
            tot = _filing_price_point(r)  # price column first, same source as the cluster chart
            if tot:
                date, _price, shares, value = tot
                s["shares"] += shares
                s["value"] += value
                s["points"].append({
                    "date": date,
                    "timestamp": r.get("timestamp") or r.get("created_at"),
                    "direction": r["_dir"],
                    "price": _price,
                    "shares": shares,
                    "value": value,
                })
                if r["_dir"] == "buy":
                    s["buy_value"] += value
                    s["buy_filings"] += 1
                elif r["_dir"] == "sell":
                    s["sell_value"] += value
                    s["sell_filings"] += 1
            fd = r["_date"].strftime("%Y-%m-%d")
            s["first"] = fd if s["first"] is None else min(s["first"], fd)
            s["last"] = fd if s["last"] is None else max(s["last"], fd)
            a = _safe_float(r.get("share_percentage_after"))
            if a is not None:
                s["own"] = a  # latest wins (recs ascending)

        stocks = []
        for sym, s in per_sym.items():
            dirs = set(s["dirs"])
            direction = "buy" if dirs <= {"buy"} else "sell" if dirs <= {"sell"} else "mixed"
            stocks.append({
                "symbol": sym, "base_symbol": str(sym).upper().split(".")[0],
                "direction": direction, "filings": s["filings"],
                "shares": s["shares"], "value": s["value"],
                "buy_value": s["buy_value"], "sell_value": s["sell_value"],
                "buy_filings": s["buy_filings"], "sell_filings": s["sell_filings"],
                "first_date": s["first"], "last_date": s["last"],
                "ownership_after": s["own"],
                "points": sorted(s["points"], key=lambda p: (p.get("date") or "", p.get("direction") or "")),
            })
        stocks.sort(key=lambda x: x["value"], reverse=True)

        total_value = sum(x["value"] for x in stocks)
        if total_value < min_value:
            continue
        buy_value = sum(x["buy_value"] for x in stocks)
        sell_value = sum(x["sell_value"] for x in stocks)
        n_buy = sum(1 for x in stocks if x["direction"] == "buy")
        n_sell = sum(1 for x in stocks if x["direction"] == "sell")
        n_mixed = sum(1 for x in stocks if x["direction"] == "mixed")
        all_dates = [x["first"] for x in per_sym.values()] + [x["last"] for x in per_sym.values()]
        all_dates = [d for d in all_dates if d]

        crosses.append({
            "holder_name": display_name.get(hkey, hkey.title()),
            "stocks": stocks,
            "n_symbols": len(stocks),
            "total_value": total_value,
            "buy_value": buy_value,
            "sell_value": sell_value,
            "n_buy": n_buy,
            "n_sell": n_sell,
            "n_mixed": n_mixed,
            "mixed": len({x["direction"] for x in stocks}) > 1 or n_mixed > 0,
            "first_date": min(all_dates) if all_dates else lo.strftime("%Y-%m-%d"),
            "last_date": max(all_dates) if all_dates else anchor.strftime("%Y-%m-%d"),
            "window_start": lo.strftime("%Y-%m-%d"),
            "window_end": anchor.strftime("%Y-%m-%d"),
            "context": in_win[-1].get("context"),
            # Trigger fields — let the signal engine treat a cross like cluster/chain.
            # Holder-pivoted: ONE rotation story per holder (not per symbol/direction).
            # progress_count = breadth, so a re-fire ("update") means a NEW distinct
            # stock was added (2->3); completed_date = latest filing = freshness anchor.
            "kind": "cross",
            "signal_key": f"cross:{hkey}",
            "progress_count": len(stocks),
            "completed_date": anchor.strftime("%Y-%m-%d"),
            "completing_filing_id": recs[-1].get("id"),
        })

    return sorted(crosses, key=lambda c: c["total_value"], reverse=True)
