"""Thin HTTP client for the Mailroom social API (api.mailroom.supertype.ai).

Mailroom now owns the post queue, the image hosting and the publishing that
social_queue.py + publisher.py used to do against Supabase - this module is
the only place that talks to it. Needs MAILROOM_API_URL and MAILROOM_API_KEY
in the environment; the key identifies the user, so no user id is ever sent.

MAILROOM_API_URL is the API base, which already carries whatever prefix the
deployment uses - "https://mailroom.supertype.ai/api/v1" when the API is
served path-based off the app host, or "https://api.mailroom.supertype.ai"
when it's on its own subdomain (which rewrites the short paths internally).
Paths here are always the short form: "/social/posts".
"""

import os
import random
import time

import requests


TIMEOUT_S = 30
MAX_ATTEMPTS = 5

# Rate limits are per-minute buckets, so a 429 needs the retries to span more
# than a minute - a few seconds of backoff would just burn every attempt
# inside the same bucket. 409 is different again: it means a request with the
# same Idempotency-Key is still in flight, and Mailroom only lets a later
# caller take that pending row over once it's 5 minutes stale, so that
# schedule has to walk past the 5-minute mark rather than give up before it.
_BACKOFF_S = (5, 15, 30, 60)
_CONFLICT_BACKOFF_S = (30, 60, 120, 180)

_session = None


class MailroomError(RuntimeError):
    def __init__(self, status, name, message):
        super().__init__(f"Mailroom {status} {name}: {message}")
        self.status = status
        self.name = name
        self.message = message


def _base_url() -> str:
    try:
        from dotenv import load_dotenv

        load_dotenv()
    except ModuleNotFoundError:
        pass

    url = os.getenv("MAILROOM_API_URL")
    if not url:
        raise RuntimeError("MAILROOM_API_URL is required.")
    return url.rstrip("/")


def _client() -> requests.Session:
    global _session
    if _session is None:
        key = os.getenv("MAILROOM_API_KEY")
        if not key:
            raise RuntimeError("MAILROOM_API_KEY is required.")
        _session = requests.Session()
        _session.headers["Authorization"] = f"Bearer {key}"
    return _session


def _error(response) -> MailroomError:
    try:
        body = response.json()
    except ValueError:
        body = {}
    return MailroomError(
        response.status_code,
        body.get("name") or "http_error",
        body.get("message") or response.text[:200],
    )


def request(method: str, path: str, *, idempotency_key: str | None = None, **kwargs) -> dict:
    """One API call, retried on the statuses that are worth retrying. 4xx
    other than 409/429 is a caller error - raised immediately, since a retry
    would only reproduce it."""
    url = f"{_base_url()}{path}"
    session = _client()
    headers = dict(kwargs.pop("headers", None) or {})
    if idempotency_key:
        headers["Idempotency-Key"] = idempotency_key

    last_error = None
    for attempt in range(MAX_ATTEMPTS):
        try:
            response = session.request(method, url, headers=headers, timeout=TIMEOUT_S, **kwargs)
        except requests.RequestException as error:
            last_error = MailroomError(0, "connection_error", str(error))
            response = None
        else:
            if response.ok:
                return response.json()
            last_error = _error(response)
            if response.status_code not in (409, 429) and response.status_code < 500:
                raise last_error

        if attempt == MAX_ATTEMPTS - 1:
            break
        schedule = _CONFLICT_BACKOFF_S if response is not None and response.status_code == 409 else _BACKOFF_S
        # Jitter so a batch of parallel generator jobs doesn't retry in lockstep.
        time.sleep(schedule[min(attempt, len(schedule) - 1)] * (1 + random.random() * 0.2))

    raise last_error


def get(path: str, **kwargs) -> dict:
    return request("GET", path, **kwargs)


def post(path: str, **kwargs) -> dict:
    return request("POST", path, **kwargs)
