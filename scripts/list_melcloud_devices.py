"""Opcional. Ejecuta esto UNA VEZ en tu ordenador (no en GitHub Actions) para
comprobar que ves tus dos splits antes de confiar en el monitor automático.
No hace falta anotar los DeviceID en ningún sitio: monitor.py los descubre
solo en cada ejecucion. Este script es solo para verificar visualmente.
"""
import getpass

import requests

BASE = "https://app.melcloud.com/Mitsubishi.Wifi.Client"

email = input("MELCloud email: ")
password = getpass.getpass("MELCloud password: ")

login = requests.post(f"{BASE}/Login/ClientLogin", json={
    "Email": email, "Password": password, "Language": 0,
    "AppVersion": "1.34.4.0", "Persist": True, "CaptchaResponse": None,
}, timeout=20).json()

if login.get("ErrorId") is not None:
    raise SystemExit(f"Login fallido: {login}")

context_key = login["LoginData"]["ContextKey"]
buildings = requests.get(
    f"{BASE}/User/ListDevices",
    headers={"X-MitsContextKey": context_key},
    timeout=20,
).json()


def walk(entries, building_id):
    for entry in entries:
        dev = entry.get("Device")
        if dev is not None:
            tipo = {0: "ATA (split)", 1: "ATW (calefaccion)", 3: "ERV (ventilacion)"}.get(
                dev.get("DeviceType"), f"tipo {dev.get('DeviceType')}"
            )
            print(f"  {entry.get('DeviceName', '(sin nombre)'):20s} [{tipo}] "
                  f"DeviceID={entry['DeviceID']}  BuildingID={building_id}  "
                  f"Power={dev.get('Power')}")


for b in buildings:
    print(f"Building: {b.get('Name')} (ID={b['ID']})")
    s = b["Structure"]
    walk(s.get("Devices", []), b["ID"])
    for area in s.get("Areas", []):
        walk(area.get("Devices", []), b["ID"])
    for floor in s.get("Floors", []):
        walk(floor.get("Devices", []), b["ID"])
        for area in floor.get("Areas", []):
            walk(area.get("Devices", []), b["ID"])
