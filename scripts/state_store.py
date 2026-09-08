"""Lee/escribe state.json y añade una línea a history.log en cada ejecución."""
import json
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
STATE_PATH = REPO_ROOT / "state.json"
HISTORY_PATH = REPO_ROOT / "history.log"
HISTORY_MAX_LINES = 30000  # tope para no dejar crecer el fichero sin límite

DEFAULT_STATE = {
    "confirmed_state": "empty",   # "empty" | "full"
    "action": "none",             # "none" | "off_sent" | "confirmed_off" | "relay_fallback"
    "splits_on_before": {},       # {device_id: bool} - foto de qué estaba encendido
    "off_sent_at": None,
}


def load() -> dict:
    if STATE_PATH.exists():
        state = json.loads(STATE_PATH.read_text())
        return {**DEFAULT_STATE, **state}
    return dict(DEFAULT_STATE)


def _append_history(line: str) -> None:
    with HISTORY_PATH.open("a", encoding="utf-8") as f:
        f.write(line + "\n")

    lines = HISTORY_PATH.read_text(encoding="utf-8").splitlines()
    if len(lines) > HISTORY_MAX_LINES:
        HISTORY_PATH.write_text("\n".join(lines[-HISTORY_MAX_LINES:]) + "\n", encoding="utf-8")


def save_and_commit(state: dict, history_line: str, commit_message: str) -> None:
    """Guarda state.json y añade la línea a history.log; commit siempre, cada ejecución."""
    STATE_PATH.write_text(json.dumps(state, indent=2, ensure_ascii=False))
    _append_history(history_line)

    subprocess.run(["git", "config", "user.name", "ac-garrafa-bot"], check=True)
    subprocess.run(["git", "config", "user.email", "actions@users.noreply.github.com"], check=True)
    subprocess.run(["git", "add", str(STATE_PATH), str(HISTORY_PATH)], check=True)
    subprocess.run(["git", "commit", "-m", commit_message], check=True)
    subprocess.run(["git", "push"], check=True)
