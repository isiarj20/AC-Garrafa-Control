"""Sondea el input SW del Shelly y mantiene sincronizado el estado de los
splits, mandando el apagado real por MELCloud en vez de cortar la corriente.
El corte del relé del Shelly queda solo como fallback de seguridad.
"""
import datetime as dt
import time


import melcloud_client as melcloud
import shelly_client as shelly
import state_store


FALLBACK_MINUTES = 10          # si MELCloud no baja el consumo en este tiempo, se corta el relé
STANDBY_POWER_W = 15           # por debajo de esto, consideramos las unidades realmente apagadas
RELAY_BOOT_GRACE_SECONDS = 45  # espera a que los adaptadores wifi arranquen tras un fallback
KEEPALIVE_DAYS = 40            # commit trivial si no ha habido actividad real en este tiempo


def now() -> dt.datetime:
    return dt.datetime.now(dt.timezone.utc)




def handle_fill_confirmed(state: dict) -> dict:
    context_key = melcloud.login()
    devices = melcloud.list_ata_devices(context_key)
     if not devices:
        raise RuntimeError(
            "MELCloud no devolvio ningun split (ListDevices vacio o filtro "
            "DeviceType sin coincidencias) - abortando en vez de fingir exito"
        )

    state["splits_on_before"] = {d["device_id"]: d["power"] for d in devices}
    for d in devices:
        if d["power"]:
            melcloud.set_power(context_key, d["device_id"], d["building_id"], power_on=False)


    state["action"] = "off_sent"
    state["off_sent_at"] = now().isoformat()
    return state




def handle_off_pending(state: dict, shelly_status: dict) -> dict:
    if shelly_status["power_w"] < STANDBY_POWER_W:
        state["action"] = "confirmed_off"
        return state


    sent_at = dt.datetime.fromisoformat(state["off_sent_at"])
    if (now() - sent_at).total_seconds() > FALLBACK_MINUTES * 60:
        shelly.set_relay(turn_on=False)
        state["action"] = "relay_fallback"
    return state




def handle_empty_confirmed(state: dict, shelly_status: dict) -> dict:
    if state["action"] == "relay_fallback" and not shelly_status["relay_on"]:
        shelly.set_relay(turn_on=True)
        time.sleep(RELAY_BOOT_GRACE_SECONDS)


    context_key = melcloud.login()
    devices = melcloud.list_ata_devices(context_key)
    by_id = {str(d["device_id"]): d for d in devices}


    for device_id, was_on in state["splits_on_before"].items():
        if was_on and str(device_id) in by_id:
            d = by_id[str(device_id)]
            melcloud.set_power(
                context_key,
                int(device_id),
                d["building_id"],
                power_on=True
            )


    state["action"] = "none"
    state["splits_on_before"] = {}
    state["off_sent_at"] = None
    return state




def main() -> None:
    state = state_store.load()
    shelly_status = shelly.get_status()
    raw = shelly_status["sw_closed"]


    # Sin debounce: al sondear solo cada 5 min (mínimo de GitHub Actions), un
    # toque accidental de un par de segundos casi nunca coincide con un
    # sondeo, así que actuar sobre la primera lectura ya es seguro y, sobre
    # todo, rápido.
    became_full = raw and state["confirmed_state"] == "empty"
    became_empty = not raw and state["confirmed_state"] == "full"


    message = None


    if became_full:
        state["confirmed_state"] = "full"
        state = handle_fill_confirmed(state)
        message = "Garrafa llena: apagado enviado por MELCloud"
    elif became_empty:
        state["confirmed_state"] = "empty"
        state = handle_empty_confirmed(state, shelly_status)
        message = "Garrafa vacia: splits restaurados a su estado previo"
    elif state["confirmed_state"] == "full" and state["action"] == "off_sent":
        state = handle_off_pending(state, shelly_status)
        if state["action"] == "confirmed_off":
            message = "Apagado confirmado por caida de consumo"
        elif state["action"] == "relay_fallback":
            message = "Fallback: rele cortado (MELCloud no confirmo a tiempo)"


    if message is None:
        last_commit = state.get("last_commit_at")
        stale = last_commit is None or (
            now() - dt.datetime.fromisoformat(last_commit)
        ).days >= KEEPALIVE_DAYS
        if stale:
            state["last_commit_at"] = now().isoformat()
            state_store.save_and_commit(state, "keepalive: sin cambios de estado")
        return


    state["last_commit_at"] = now().isoformat()
    state_store.save_and_commit(state, message)




if __name__ == "__main__":
    main()
