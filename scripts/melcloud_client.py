"""Cliente mínimo para la API (no oficial) de MELCloud.

No hace falta guardar los DeviceID de cada split en ningún sitio: se listan
en cada ejecución llamando a ListDevices, así que solo necesitas el email y
la contraseña de tu cuenta MELCloud como secrets.
"""
import os

import requests

BASE = "https://app.melcloud.com/Mitsubishi.Wifi.Client"
EMAIL = os.environ["MELCLOUD_EMAIL"]
PASSWORD = os.environ["MELCLOUD_PASSWORD"]

DEVICE_TYPE_ATA = 0   # split / aire acondicionado (frente a ATW=calefacción o ERV=ventilación)
POWER_FLAG = 0x01     # EffectiveFlags: bit que indica "solo cambio Power"


def login() -> str:
    resp = requests.post(
        f"{BASE}/Login/ClientLogin",
        json={
            "Email": EMAIL,
            "Password": PASSWORD,
            "Language": 0,
            "AppVersion": "1.34.4.0",
            "Persist": True,
            "CaptchaResponse": None,
        },
        timeout=20,
    )
    resp.raise_for_status()
    data = resp.json()
    if not data.get("LoginData"):
        raise RuntimeError(f"MELCloud login failed: {data}")
    return data["LoginData"]["ContextKey"]


def _headers(context_key: str) -> dict:
    return {"X-MitsContextKey": context_key}


def list_ata_devices(context_key: str) -> list[dict]:
    """Devuelve [{device_id, building_id, name, power}, ...] solo para splits."""
    resp = requests.get(f"{BASE}/User/ListDevices", headers=_headers(context_key), timeout=20)
    resp.raise_for_status()
    buildings = resp.json()

    devices: list[dict] = []

    def _walk(entries, building_id):
        for entry in entries:
            dev = entry.get("Device")
            if dev is not None and dev.get("DeviceType") == DEVICE_TYPE_ATA:
                devices.append({
                    "device_id": entry["DeviceID"],
                    "building_id": building_id,
                    "name": entry.get("DeviceName", ""),
                    "power": bool(dev.get("Power")),
                })

    for building in buildings:
        bid = building["ID"]
        structure = building["Structure"]
        _walk(structure.get("Devices", []), bid)
        for area in structure.get("Areas", []):
            _walk(area.get("Devices", []), bid)
        for floor in structure.get("Floors", []):
            _walk(floor.get("Devices", []), bid)
            for area in floor.get("Areas", []):
                _walk(area.get("Devices", []), bid)

    return devices


def get_device_state(context_key: str, device_id: str, building_id: int) -> dict:
    resp = requests.get(
        f"{BASE}/Device/Get",
        params={"id": device_id, "buildingID": building_id},
        headers=_headers(context_key),
        timeout=20,
    )
    resp.raise_for_status()
    return resp.json()


def set_power(context_key: str, device_id: str, building_id: int, power_on: bool) -> None:
    """Enciende/apaga un split sin tocar ningún otro ajuste (modo, temperatura...)."""
    state = get_device_state(context_key, device_id, building_id)
    state["Power"] = power_on
    state["EffectiveFlags"] = POWER_FLAG
    state["HasPendingCommand"] = True

    resp = requests.post(
        f"{BASE}/Device/SetAta",
        json=state,
        headers=_headers(context_key),
        timeout=20,
    )
    resp.raise_for_status()
