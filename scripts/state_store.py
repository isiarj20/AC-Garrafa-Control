"""Lee/escribe state.json y hace commit+push SOLO cuando cambia de verdad."""
import json
import subprocess
from pathlib import Path

STATE_PATH = Path(__file__).resolve().parent.parent / "state.json"

DEFAULT_STATE = {
    "confirmed_state": "empty",   # "empty" | "full"  (estado ya debounced)
    "action": "none",             # "none" | "off_sent" | "confirmed_off" | "relay_fallback"
    "splits_on_before": {},       # {device_id: bool} - foto de qué estaba encendido
    "off_sent_at": None,
    "last_commit_at": None,
}


def load() -> dict:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        return {**DEFAULT_STATE, **state}
    return dict(DEFAULT_STATE)


def save_and_commit(state: dict, message: str) -> None:
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))

    result = subprocess.run(
        ["git", "status", "--porcelain", str(STATE_PATH)],
        capture_output=True, text=True, check=True,
    )
    if not result.stdout.strip():
        return  # nada que commitear

    subprocess.run(["git", "config", "user.name", "ac-garrafa-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", str(STATE_PATH)], check=True)
    subprocess.run(["git", "commit", "-m", message], check=True)
    subprocess.run(["git", "push"], check=True)
