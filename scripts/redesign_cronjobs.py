"""cron-job.org schedule for the redesigned posts, and switching the old jobs off.

Every redesigned post runs through one workflow, redesign_social.yml, dispatched with {"post": ..., "dry_run":
"false"}. Each job fires ~30 min before that post's go-live time (post_routing.POST_SCHEDULE_BY_CONTENT_TYPE) so
the render can finish; Mailroom holds the post until scheduled_at.

Usage (needs CRON_JOB_ORG_API_KEY; --create also needs GH_PAT):
  python scripts/redesign_cronjobs.py                    # dry run: print the plan, touch nothing
  python scripts/redesign_cronjobs.py --list             # list every cron-job.org job for this repo
  python scripts/redesign_cronjobs.py --create --execute # create the 9 new jobs, DISABLED
  python scripts/redesign_cronjobs.py --disable-old --execute
                                                         # disable (not delete) every other job for this repo
  python scripts/redesign_cronjobs.py --enable-new --execute
                                                         # turn the 9 new jobs on, once a manual dry run looks right
"""
import argparse
import json
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from seed_cronjobs import ANY_DAY, CRON_API, REPO, build_payload, env, put_job, redact_pat, summarize  # noqa: E402

WORKFLOW = "redesign_social.yml"
PREFIX = "redesign — "
DAILY = ANY_DAY

# (post, generate hour, minute WIB, weekdays [0=Sun..6=Sat]) - go-live is 30 min later
NEW_JOBS = [
    dict(post="weekly-calendar", hour=12, minute=30, wdays=[1]),    # Mon 13:00
    dict(post="insider-carousel", hour=12, minute=30, wdays=[2]),   # Tue 13:00
    dict(post="news-flash", hour=16, minute=0, wdays=[3]),          # Wed 16:30
    dict(post="earnings-carousel", hour=12, minute=30, wdays=[4]),  # Thu 13:00
    dict(post="story-crossing", hour=9, minute=30, wdays=DAILY),    # daily 10:00
    dict(post="story-news", hour=12, minute=30, wdays=DAILY),       # daily 13:00
    dict(post="story-volume", hour=19, minute=30, wdays=DAILY),     # daily 20:00 (skips non-trading days)
    dict(post="story-broker", hour=20, minute=0, wdays=DAILY),      # daily 20:30 (skips non-trading days)
    dict(post="story-movers", hour=20, minute=30, wdays=DAILY),     # daily 21:00 (skips non-trading days)
]


def cfg_for(j):
    return dict(title=PREFIX + j["post"], workflow=WORKFLOW, hour=j["hour"], minute=j["minute"],
                wdays=j["wdays"], mdays=ANY_DAY, inputs={"post": j["post"], "dry_run": "false"})


def api(method, path, key, body=None):
    req = urllib.request.Request(f"{CRON_API}{path}", method=method,
                                 data=json.dumps(body).encode() if body is not None else None,
                                 headers={"Authorization": f"Bearer {key}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=15) as r:
            return json.loads(r.read() or b"{}")
    except urllib.error.HTTPError as e:
        raise SystemExit(f"HTTP {e.code} on {method} {path}: {e.read().decode()}")


def repo_jobs(key):
    """Every cron-job.org job that dispatches a workflow in this repo."""
    return [j for j in api("GET", "/jobs", key).get("jobs", []) if f"/repos/{REPO}/" in (j.get("url") or "")]


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--list", action="store_true")
    p.add_argument("--create", action="store_true", help="create the new jobs (disabled)")
    p.add_argument("--disable-old", action="store_true", help="disable every repo job that isn't a redesign job")
    p.add_argument("--enable-new", action="store_true", help="enable the redesign jobs")
    p.add_argument("--execute", action="store_true", help="actually call cron-job.org (default: dry run)")
    p.add_argument("--delay", type=float, default=3.0)
    a = p.parse_args()

    print(f"# {len(NEW_JOBS)} redesign jobs -> {WORKFLOW} (Asia/Jakarta)")
    for j in NEW_JOBS:
        print(summarize(cfg_for(j)))
    if not (a.list or a.create or a.disable_old or a.enable_new):
        print("\nplan only. Use --list / --create / --disable-old / --enable-new, with --execute to apply.")
        return

    key = env("CRON_JOB_ORG_API_KEY")
    jobs = repo_jobs(key)
    new_titles = {PREFIX + j["post"] for j in NEW_JOBS}
    if a.list:
        print(f"\n# {len(jobs)} cron-job.org jobs for {REPO}")
        for j in sorted(jobs, key=lambda j: j.get("title", "")):
            print(f"  [{'on ' if j.get('enabled') else 'off'}] {j['jobId']:>9}  {j.get('title')}")

    if a.create:
        have = {j.get("title") for j in jobs}
        todo = [j for j in NEW_JOBS if PREFIX + j["post"] not in have]
        print(f"\ncreate {len(todo)} job(s) (disabled){'' if a.execute else ' - dry run'}:")
        gh_pat = env("GH_PAT")
        for j in todo:
            payload = build_payload(cfg_for(j), gh_pat, enabled=False)
            if not a.execute:
                print(json.dumps(redact_pat(payload)["job"]["extendedData"]["body"]), "->", payload["job"]["title"])
                continue
            print("  created", put_job(payload, key).get("jobId"), payload["job"]["title"])
            time.sleep(a.delay)

    for flag, want, pick in ((a.disable_old, False, lambda j: j.get("title") not in new_titles),
                             (a.enable_new, True, lambda j: j.get("title") in new_titles)):
        if not flag:
            continue
        hits = [j for j in jobs if pick(j) and bool(j.get("enabled")) != want]
        print(f"\n{'enable' if want else 'disable'} {len(hits)} job(s){'' if a.execute else ' - dry run'}:")
        for j in hits:
            print(f"  {j['jobId']:>9}  {j.get('title')}")
            if a.execute:
                api("PATCH", f"/jobs/{j['jobId']}", key, {"job": {"enabled": want}})
                time.sleep(a.delay)


if __name__ == "__main__":
    main()
