"""Map a raw Tesla ``get_vehicle_data`` payload into the flat dict the CoT layer consumes.

Pure functions (no I/O, no state) — extracted from ``TeslaCoT`` so the mapping is
independently testable and reusable.
"""
import hashlib
import time

_MODEL_NAMES = {
    "models": "Model S",
    "modelx": "Model X",
    "model3": "Model 3",
    "modely": "Model Y",
    "cybertruck": "Cybertruck",
}


def vehicle_uid(vehicle: dict) -> str:
    """Stable CoT UID derived from the vehicle's owner-api id."""
    vehicle_id = vehicle.get("id_s", vehicle.get("vehicle_id", "unknown"))
    return f"TESLA-{hashlib.md5(str(vehicle_id).encode(), usedforsecurity=False).hexdigest()[:8]}"


def build_vehicle_model(vehicle_config: dict) -> str:
    """Human model string from vehicle_config, e.g. ``2024 Model Y Performance``.

    Trim codes: ``p`` -> Performance, ``l`` -> Long Range, otherwise the raw
    badge uppercased.
    """
    car_type = vehicle_config.get("car_type", "")
    year = vehicle_config.get("year", "")
    trim = vehicle_config.get("trim_badging", "")

    model_name = _MODEL_NAMES.get(car_type.lower(), car_type)
    if trim:
        if trim.lower().startswith("p"):
            variant = "Performance"
        elif trim.lower().startswith("l"):
            variant = "Long Range"
        else:
            variant = trim.upper()
        model = f"{model_name} {variant}"
    else:
        model = model_name
    return f"{year} {model}" if year else model


def map_vehicle_data(vehicle_data: dict, vehicle: dict) -> dict:
    """Flatten a Tesla ``get_vehicle_data`` response into the CoT data dict."""
    drive_state = vehicle_data.get("drive_state", {})
    charge_state = vehicle_data.get("charge_state", {})
    vehicle_state = vehicle_data.get("vehicle_state", {})
    climate_state = vehicle_data.get("climate_state", {})
    vehicle_config = vehicle_data.get("vehicle_config", {})
    display_name = vehicle.get("display_name", "Tesla")

    return {
        "UID": vehicle_uid(vehicle),
        "latitude": drive_state.get("latitude"),
        "longitude": drive_state.get("longitude"),
        "speed": drive_state.get("speed", 0),
        "heading": drive_state.get("heading", 0),
        # Tesla doesn't provide elevation; this field stands in for it.
        "elevation": drive_state.get("native_location_supported", 0),
        "battery_level": charge_state.get("battery_level", 0),
        "charging_state": charge_state.get("charging_state", "Disconnected"),
        "vehicle_name": vehicle_state.get("vehicle_name", display_name),
        "display_name": display_name,
        "vehicle_model": build_vehicle_model(vehicle_config),
        "inside_temp": climate_state.get("inside_temp"),
        "outside_temp": climate_state.get("outside_temp"),
        "sentry_mode": vehicle_state.get("sentry_mode", False),
        "locked": vehicle_state.get("locked", None),
        "shift_state": drive_state.get("shift_state"),  # P, D, R, N
        "battery_range": charge_state.get("battery_range"),  # miles remaining
        "is_climate_on": climate_state.get("is_climate_on", False),
        "charge_port_door_open": charge_state.get("charge_port_door_open", False),
        "time_to_full_charge": charge_state.get("time_to_full_charge", 0),
        "charge_limit_soc": charge_state.get("charge_limit_soc", 80),
        "minutes_to_full_charge": charge_state.get("minutes_to_full_charge", 0),
        # Window/trunk positions (0 = closed, >0 = open)
        "fd_window": vehicle_state.get("fd_window", 0),
        "fp_window": vehicle_state.get("fp_window", 0),
        "rd_window": vehicle_state.get("rd_window", 0),
        "rp_window": vehicle_state.get("rp_window", 0),
        "ft": vehicle_state.get("ft", 0),
        "rt": vehicle_state.get("rt", 0),
        "autopilot_state": vehicle_state.get("autopilot_state", 0),
        "autopilot_style": vehicle_state.get("autopilot_style"),
        "autopark_state": vehicle_state.get("autopark_state_v3"),
        "timestamp": time.time(),
    }
