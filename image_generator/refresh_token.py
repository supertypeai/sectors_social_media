"""Monthly long-lived-token refresh for Instagram and Threads.

Fetches a refreshed access token from Meta for each configured platform and
persists it as a GitHub Actions secret via the `gh` CLI, so the next
publisher.py run (which reads IG_ACCESS_TOKEN/THREADS_ACCESS_TOKEN from the
environment/secrets) picks up the new value automatically.

Persisting the secret requires a PAT with repo "secrets: write" permission
in GH_PAT (or GH_TOKEN) - the default GITHUB_TOKEN provided automatically in
Actions runs cannot write secrets. Without it, the refreshed token is only
printed, not saved - see the "Just log it" fallback below.

Run via: python -m image_generator.refresh_token
"""

import os
import subprocess
import sys

import requests

try:
    from dotenv import load_dotenv

    load_dotenv()
except ModuleNotFoundError:
    pass


IG_REFRESH_URL = "https://graph.instagram.com/refresh_access_token"
THREADS_REFRESH_URL = "https://graph.threads.net/refresh_access_token"
REQUEST_TIMEOUT_S = 30


def _gh_secret_set(name: str, value: str) -> bool:
    pat = os.getenv("GH_PAT") or os.getenv("GH_TOKEN")
    if not pat:
        print(f"GH_PAT/GH_TOKEN not set - cannot persist refreshed {name} automatically.")
        print(f"Update the '{name}' secret manually with the value below:")
        print(value)
        return False

    env = os.environ.copy()
    env["GH_TOKEN"] = pat
    result = subprocess.run(
        ["gh", "secret", "set", name],
        input=value.encode(),
        env=env,
        capture_output=True,
    )
    if result.returncode != 0:
        print(f"Failed to set secret {name}: {result.stderr.decode().strip()}", file=sys.stderr)
        return False

    print(f"Updated secret {name}")
    return True


def refresh_ig() -> bool:
    token = os.getenv("IG_ACCESS_TOKEN")
    if not token:
        print("IG_ACCESS_TOKEN not set, skipping IG refresh")
        return True

    resp = requests.get(
        IG_REFRESH_URL,
        params={"grant_type": "ig_refresh_token", "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    new_token = data.get("access_token")
    if not new_token:
        print(f"IG refresh failed: {data}", file=sys.stderr)
        return False

    print(f"IG token refreshed, expires_in={data.get('expires_in')}s")
    return _gh_secret_set("IG_ACCESS_TOKEN", new_token)


def refresh_threads() -> bool:
    token = os.getenv("THREADS_ACCESS_TOKEN")
    if not token:
        print("THREADS_ACCESS_TOKEN not set, skipping Threads refresh")
        return True

    resp = requests.get(
        THREADS_REFRESH_URL,
        params={"grant_type": "th_refresh_token", "access_token": token},
        timeout=REQUEST_TIMEOUT_S,
    )
    data = resp.json()
    new_token = data.get("access_token")
    if not new_token:
        print(f"Threads refresh failed: {data}", file=sys.stderr)
        return False

    print(f"Threads token refreshed, expires_in={data.get('expires_in')}s")
    return _gh_secret_set("THREADS_ACCESS_TOKEN", new_token)


def main():
    ok_ig = refresh_ig()
    ok_threads = refresh_threads()
    if not (ok_ig and ok_threads):
        sys.exit(1)


if __name__ == "__main__":
    main()
