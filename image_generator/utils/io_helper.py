from pathlib import Path

import json 


DIVIDEND_STATE_PATH = Path("state/posted_dividend.json")


def load_dividend_state() -> dict[str, dict]:
    path = DIVIDEND_STATE_PATH

    if path.exists():
        try:
            data = json.loads(path.read_text(encoding="utf-8"))
            data.setdefault("dividends", {})
            return data

        except (ValueError, OSError):
            pass

    return {"dividends": {}}


def save_dividend_state(state: dict[str, dict]) -> None:
    DIVIDEND_STATE_PATH.parent.mkdir(parents=True, exist_ok=True)
    
    DIVIDEND_STATE_PATH.write_text(
        json.dumps(state, indent=2, sort_keys=True), encoding="utf-8"
    )
