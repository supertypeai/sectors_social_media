"""Seed cron-job.org jobs that trigger this repo's GH Actions workflows.

Why this exists:
  GitHub Actions free-tier cron drifted 4-5h on top-of-hour schedules. The 11
  social workflows were migrated from schedule: cron to workflow_dispatch only;
  cron-job.org fires the dispatch via GitHub's REST API at sub-minute precision.
  This script is the bulk-seeder for the cron-job.org side.

Setup:
  1. Generate a cron-job.org API key:  https://console.cron-job.org → Settings → API
  2. Generate a GH PAT (fine-grained, single repo, Actions: Read+Write):
     https://github.com/settings/personal-access-tokens/new
  3. export CRON_JOB_ORG_API_KEY=...
  4. export GH_PAT=github_pat_...

Usage:
  # Default: dry-run, prints payloads + a sanity summary, does NOT call the API.
  python scripts/seed_cronjobs.py

  # Real: creates 16 jobs as DISABLED. Review in cron-job.org dashboard, then
  # enable when ready.
  python scripts/seed_cronjobs.py --execute

  # Real + enabled immediately (skip the review step). Use only after you've
  # validated the loop end-to-end once.
  python scripts/seed_cronjobs.py --execute --enabled
"""

import argparse
import json
import os
import sys
import time
import urllib.error
import urllib.request

CRON_API = "https://api.cron-job.org"
REPO = "supertypeai/sectors_social_media"
TZ = "Asia/Jakarta"  # WIB, UTC+7, no DST

# cron-job.org wday convention: 0=Sun, 1=Mon, ..., 6=Sat. -1 = every.
MON_FRI = [1, 2, 3, 4, 5]
TUE_SAT = [2, 3, 4, 5, 6]
ANY_DAY = [-1]

# Each entry: title, workflow filename, WIB hour, WIB minute, wdays, mdays, body inputs.
# Hours/minutes are in WIB (the schedule's timezone). All converted from the
# original GH UTC crons by adding 7.
JOBS = [
    # news_social — 05:00 UTC Mon-Fri = 12:00 WIB
    dict(title="news_social — news-tier1",
         workflow="news_social.yml",
         hour=12, minute=0, wdays=MON_FRI, mdays=ANY_DAY,
         inputs={"mode": "news-tier1"}),
    # plain_filings — 00:00 UTC Tue-Sat = 07:00 WIB Tue-Sat
    dict(title="plain_filings_social",
         workflow="plain_filings_social.yml",
         hour=7, minute=0, wdays=TUE_SAT, mdays=ANY_DAY),
    # agm_social — 11:00 UTC daily = 18:00 WIB
    dict(title="agm_social",
         workflow="agm_social.yml",
         hour=18, minute=0, wdays=ANY_DAY, mdays=ANY_DAY),
    # broker_social bandar — 11:30 UTC Mon-Fri = 18:30 WIB
    dict(title="broker_social — bandar",
         workflow="broker_social.yml",
         hour=18, minute=30, wdays=MON_FRI, mdays=ANY_DAY,
         inputs={"mode": "broker-bandar", "dry_run": "false"}),
    # broker_social trending — same time
    dict(title="broker_social — trending",
         workflow="broker_social.yml",
         hour=18, minute=30, wdays=MON_FRI, mdays=ANY_DAY,
         inputs={"mode": "broker-trending", "dry_run": "false"}),
    # broker_social weekly — Friday only
    dict(title="broker_social — weekly",
         workflow="broker_social.yml",
         hour=18, minute=30, wdays=[5], mdays=ANY_DAY,
         inputs={"mode": "broker-weekly", "dry_run": "false"}),
    # workflow_social dividend — 12:00 UTC daily = 19:00 WIB
    dict(title="workflow_social — dividend",
         workflow="workflow_social.yml",
         hour=19, minute=0, wdays=ANY_DAY, mdays=ANY_DAY,
         inputs={"mode": "dividend"}),
    # workflow_social companies-mover — 12:00 UTC day 1 of month = 19:00 WIB day 1
    dict(title="workflow_social — companies-mover",
         workflow="workflow_social.yml",
         hour=19, minute=0, wdays=ANY_DAY, mdays=[1],
         inputs={"mode": "companies-mover"}),
    # volume_spike — 12:00 UTC Mon-Fri = 19:00 WIB
    dict(title="volume_spike_social",
         workflow="volume_spike_social.yml",
         hour=19, minute=0, wdays=MON_FRI, mdays=ANY_DAY),
    # anomaly_changes — 12:30 UTC Mon-Fri = 19:30 WIB
    dict(title="anomaly_changes_social",
         workflow="anomaly_changes_social.yml",
         hour=19, minute=30, wdays=MON_FRI, mdays=ANY_DAY),
    # insider_social signal — 13:00 UTC Mon-Fri = 20:00 WIB
    dict(title="insider_social — signal",
         workflow="insider_social.yml",
         hour=20, minute=0, wdays=MON_FRI, mdays=ANY_DAY,
         inputs={"mode": "filings-signal"}),
    # insider_social story — 13:00 UTC Sunday = 20:00 WIB Sunday
    dict(title="insider_social — story",
         workflow="insider_social.yml",
         hour=20, minute=0, wdays=[0], mdays=ANY_DAY,
         inputs={"mode": "filings-story"}),
    # earnings_social — 13:00 UTC Mon-Fri = 20:00 WIB
    dict(title="earnings_social",
         workflow="earnings_social.yml",
         hour=20, minute=0, wdays=MON_FRI, mdays=ANY_DAY),
    # workflow_social quarterly — 13:00 UTC Friday = 20:00 WIB Friday
    dict(title="workflow_social — quarterly",
         workflow="workflow_social.yml",
         hour=20, minute=0, wdays=[5], mdays=ANY_DAY,
         inputs={"mode": "quarterly"}),
    # dividend_social — 13:00 UTC Friday = 20:00 WIB Friday
    dict(title="dividend_social",
         workflow="dividend_social.yml",
         hour=20, minute=0, wdays=[5], mdays=ANY_DAY),
    # becoming_insider — 13:30 UTC Mon-Fri = 20:30 WIB
    dict(title="becoming_insider_social",
         workflow="becoming_insider_social.yml",
         hour=20, minute=30, wdays=MON_FRI, mdays=ANY_DAY),
    # workflow_social macro-news — 08:00 UTC daily = 15:00 WIB
    # (originally 13:00 WIB; Fawwaz bumped to 15:00 because the upstream
    # macro-news pipeline isn't finished running by 13:00)
    dict(title="workflow_social — macro-news",
         workflow="workflow_social.yml",
         hour=15, minute=0, wdays=ANY_DAY, mdays=ANY_DAY,
         inputs={"mode": "macro-news"}),
    # workflow_social stock-performance (weekly) — 12:00 UTC Friday = 19:00 WIB Friday
    dict(title="workflow_social — stock-performance weekly",
         workflow="workflow_social.yml",
         hour=19, minute=0, wdays=[5], mdays=ANY_DAY,
         inputs={"mode": "stock-performance", "day": "7"}),
    # workflow_social stock-performance (monthly) — 12:00 UTC day 1 = 19:00 WIB day 1
    dict(title="workflow_social — stock-performance monthly",
         workflow="workflow_social.yml",
         hour=19, minute=0, wdays=ANY_DAY, mdays=[1],
         inputs={"mode": "stock-performance", "day": "30"}),
    # ownership_board_social — 22:30 UTC last-day = 05:30 WIB on the 1st of the month
    # (monthly leaderboard, dedup'd by YYYY-MM key in posted_ownership_board.json)
    dict(title="ownership_board_social",
         workflow="ownership_board_social.yml",
         hour=5, minute=30, wdays=ANY_DAY, mdays=[1]),
    # ownership_social — 23:00 UTC Tue+Thu = 06:00 WIB Wed+Fri
    # (rotation queue, 1 post per run; ~226-name backlog runs ~2 years at 2x/week)
    dict(title="ownership_social",
         workflow="ownership_social.yml",
         hour=6, minute=0, wdays=[3, 5], mdays=ANY_DAY),
    # weekly_movers_social (W1 Weekly Wrap) — Fri 18:10 WIB
    # Sits between AGM (18:00) and broker (18:30) in the post-close Friday sequence.
    dict(title="weekly_movers_social — winners & losers",
         workflow="weekly_movers_social.yml",
         hour=18, minute=10, wdays=[5], mdays=ANY_DAY),
    # lq45_ytd_social (W2 LQ45 YTD Monthly, worst direction) — 1st of month 18:15 WIB
    dict(title="lq45_ytd_social — monthly worst",
         workflow="lq45_ytd_social.yml",
         hour=18, minute=15, wdays=ANY_DAY, mdays=[1]),
    # sector_heatmap_social (W3 Sector Pulse) — Fri 18:20 WIB
    # Sector-level counterpart to W1; fires 10 min after W1 in the same post-close pocket.
    dict(title="sector_heatmap_social — weekly",
         workflow="sector_heatmap_social.yml",
         hour=18, minute=20, wdays=[5], mdays=ANY_DAY),
    # insider_roundup_social (W4 Insider Watch) — Sat 08:00 WIB
    # Weekend digest of the week's insider buys/sells; no other Sat traffic.
    dict(title="insider_roundup_social — weekly",
         workflow="insider_roundup_social.yml",
         hour=8, minute=0, wdays=[6], mdays=ANY_DAY),
]


def env(name: str) -> str:
    v = os.environ.get(name)
    if not v:
        sys.exit(f"missing env var: {name}")
    return v


def url_for(workflow: str) -> str:
    return f"https://api.github.com/repos/{REPO}/actions/workflows/{workflow}/dispatches"


def build_body(inputs: dict | None) -> str:
    payload: dict = {"ref": "main"}
    if inputs:
        payload["inputs"] = inputs
    return json.dumps(payload)


def build_payload(cfg: dict, gh_pat: str, enabled: bool) -> dict:
    return {
        "job": {
            "url": url_for(cfg["workflow"]),
            "enabled": enabled,
            "title": cfg["title"],
            "saveResponses": True,
            "requestMethod": 1,  # POST
            "schedule": {
                "timezone": TZ,
                "expiresAt": 0,
                "minutes": [cfg["minute"]],
                "hours": [cfg["hour"]],
                "mdays": cfg["mdays"],
                "wdays": cfg["wdays"],
                "months": [-1],
            },
            "notification": {"onFailure": True, "onSuccess": False},
            "extendedData": {
                "headers": {
                    "Accept": "application/vnd.github+json",
                    "Authorization": f"Bearer {gh_pat}",
                    "X-GitHub-Api-Version": "2022-11-28",
                },
                "body": build_body(cfg.get("inputs")),
            },
        }
    }


def put_job(payload: dict, cron_key: str) -> dict:
    req = urllib.request.Request(
        f"{CRON_API}/jobs",
        data=json.dumps(payload).encode(),
        method="PUT",
        headers={
            "Authorization": f"Bearer {cron_key}",
            "Content-Type": "application/json",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return json.loads(resp.read())
    except urllib.error.HTTPError as e:
        body = e.read().decode()
        raise SystemExit(f"HTTP {e.code}: {body}")


def redact_pat(payload: dict) -> dict:
    """Return a deep copy of payload with the GH PAT redacted, safe to print."""
    import copy
    p = copy.deepcopy(payload)
    headers = p["job"]["extendedData"]["headers"]
    if "Authorization" in headers:
        headers["Authorization"] = "Bearer github_pat_***REDACTED***"
    return p


def summarize(cfg: dict) -> str:
    body = build_body(cfg.get("inputs"))
    wdays_str = (
        "any" if cfg["wdays"] == ANY_DAY
        else {tuple(MON_FRI): "Mon-Fri", tuple(TUE_SAT): "Tue-Sat"}.get(
            tuple(cfg["wdays"]),
            "/".join(["Sun","Mon","Tue","Wed","Thu","Fri","Sat"][d] for d in cfg["wdays"])
        )
    )
    mdays_str = "any" if cfg["mdays"] == ANY_DAY else "day " + "/".join(str(d) for d in cfg["mdays"])
    return (
        f"  {cfg['title']:<42} "
        f"{cfg['hour']:02d}:{cfg['minute']:02d} WIB  "
        f"{wdays_str:<7}  {mdays_str:<8}  body={body}"
    )


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--execute", action="store_true",
                   help="actually POST to cron-job.org. Default is dry-run.")
    p.add_argument("--enabled", action="store_true",
                   help="create jobs enabled. Default is disabled (review first).")
    p.add_argument("--start-from", type=int, default=1, metavar="N",
                   help="resume from job number N (1-indexed). Use after a 429.")
    p.add_argument("--delay", type=float, default=3.0, metavar="SEC",
                   help="seconds to sleep between requests (default 3.0 to avoid 429).")
    args = p.parse_args()

    gh_pat = env("GH_PAT")
    cron_key = env("CRON_JOB_ORG_API_KEY") if args.execute else "DRYRUN"

    print(f"# {len(JOBS)} jobs for {REPO} ({TZ})")
    print(f"# mode: {'EXECUTE' if args.execute else 'DRY-RUN'}  "
          f"enabled-on-create: {args.enabled}\n")

    for cfg in JOBS:
        print(summarize(cfg))

    if not args.execute:
        print("\nDry-run only. Sample payload (first job, PAT redacted):\n")
        sample = build_payload(JOBS[0], gh_pat, args.enabled)
        print(json.dumps(redact_pat(sample), indent=2))
        print("\nRerun with --execute to actually create the jobs.")
        return

    start = max(1, args.start_from)
    if start > 1:
        print(f"\ncreating jobs (resuming from #{start}, delay {args.delay}s between)...")
    else:
        print(f"\ncreating jobs (delay {args.delay}s between to avoid 429)...")

    for i, cfg in enumerate(JOBS, 1):
        if i < start:
            continue
        payload = build_payload(cfg, gh_pat, args.enabled)
        try:
            result = put_job(payload, cron_key)
        except SystemExit as e:
            if "HTTP 429" in str(e):
                print(f"\n429 rate limit at job #{i}. Resume with:")
                print(f"  python scripts/seed_cronjobs.py --execute --start-from {i} --delay {args.delay + 2}")
            raise
        jid = result.get("jobId") or result.get("id") or "?"
        print(f"  [{i:>2}/{len(JOBS)}] jobId={jid}  {cfg['title']}")
        if i < len(JOBS):
            time.sleep(args.delay)

    print(f"\nDone. View at https://console.cron-job.org/jobs")
    if not args.enabled:
        print("Jobs created DISABLED — toggle each on in the dashboard when ready.")


if __name__ == "__main__":
    main()
