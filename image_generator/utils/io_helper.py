from pathlib import Path

import json 


DIVIDEND_STATE_PATH = Path("state/posted_dividend.json")

THEME_ROTATION_PATH = Path("state/theme_rotation.json")
THEME_ROTATION_ORDER = ["default", "aurora", "ember", "neon"]

VOLUME_SPIKE_THEME_ROTATION_PATH = Path("state/volume_spike_theme_rotation.json")
VOLUME_SPIKE_THEME_ROTATION_ORDER = ["red", "blue", "orange", "green"]


def next_rotating_theme(order: list[str] = THEME_ROTATION_ORDER, path: Path = THEME_ROTATION_PATH) -> str:
    idx = 0
    if path.exists():
        try:
            idx = int(json.loads(path.read_text(encoding="utf-8")).get("index", 0))
        except (ValueError, OSError, TypeError):
            idx = 0
    theme = order[idx % len(order)]
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(
            json.dumps({"index": (idx + 1) % len(order)}, indent=2), encoding="utf-8"
        )
    except OSError:
        pass
    return theme


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
