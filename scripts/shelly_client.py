"""Cliente mínimo para la Shelly Cloud API (dispositivo Gen1: 1PM)."""
import os

import requests

SERVER = os.environ["SHELLY_SERVER_URI"].rstrip("/")
AUTH_KEY = os.environ["SHELLY_AUTH_KEY"]
DEVICE_ID = os.environ["SHELLY_DEVICE_ID"]


def get_status() -> dict:
    """Devuelve {'sw_closed': bool, 'power_w': float, 'relay_on': bool}.

    sw_closed=True significa boya activada (garrafa llena).
    """
    resp = requests.get(
        f"https://{SERVER}/device/status",
        params={"id": DEVICE_ID, "auth_key": AUTH_KEY},
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("isok"):
        raise RuntimeError(f"Shelly status error: {payload}")

    status = payload["data"]["device_status"]
    sw_closed = bool(status["inputs"][0]["input"])
    power_w = float(status["meters"][0]["power"])
    relay_on = bool(status["relays"][0]["ison"])
    return {"sw_closed": sw_closed, "power_w": power_w, "relay_on": relay_on}


def set_relay(turn_on: bool) -> None:
    """SOLO como fallback de seguridad: corta o restaura la corriente en el relé."""
    resp = requests.post(
        f"https://{SERVER}/device/relay/control",
        data={
            "id": DEVICE_ID,
            "auth_key": AUTH_KEY,
            "channel": 0,
            "turn": "on" if turn_on else "off",
        },
        timeout=15,
    )
    resp.raise_for_status()
    payload = resp.json()
    if not payload.get("isok"):
        raise RuntimeError(f"Shelly relay control error: {payload}")
