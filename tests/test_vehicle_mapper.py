"""Tests for teslaontarget.vehicle_mapper (pure Tesla-payload -> CoT dict mapping)."""
import hashlib

import pytest

from teslaontarget.vehicle_mapper import build_vehicle_model, map_vehicle_data, vehicle_uid


def _vehicle(**over):
    base = {"id_s": "3744443410507808", "display_name": "Tron"}
    base.update(over)
    return base


class TestVehicleUid:
    def test_stable_md5_of_id_s(self):
        assert vehicle_uid(_vehicle()) == "TESLA-" + hashlib.md5(b"3744443410507808", usedforsecurity=False).hexdigest()[:8]

    def test_falls_back_to_vehicle_id_key(self):
        assert vehicle_uid({"vehicle_id": "987"}) == "TESLA-" + hashlib.md5(b"987", usedforsecurity=False).hexdigest()[:8]

    def test_falls_back_to_unknown(self):
        assert vehicle_uid({}) == "TESLA-" + hashlib.md5(b"unknown", usedforsecurity=False).hexdigest()[:8]


class TestBuildVehicleModel:
    @pytest.mark.parametrize("car_type,expected", [
        ("models", "Model S"), ("modelx", "Model X"), ("model3", "Model 3"),
        ("modely", "Model Y"), ("cybertruck", "Cybertruck"),
        ("roadster", "roadster"),  # unmapped -> passthrough
    ])
    def test_model_name_mapping(self, car_type, expected):
        assert build_vehicle_model({"car_type": car_type}) == expected

    def test_performance_trim(self):
        assert build_vehicle_model({"car_type": "modely", "trim_badging": "p74d"}) == "Model Y Performance"

    def test_long_range_trim(self):
        assert build_vehicle_model({"car_type": "model3", "trim_badging": "ld"}) == "Model 3 Long Range"

    def test_other_trim_uppercased(self):
        assert build_vehicle_model({"car_type": "models", "trim_badging": "xx"}) == "Model S XX"

    def test_year_prefixed(self):
        assert build_vehicle_model(
            {"car_type": "modely", "trim_badging": "p", "year": 2024}) == "2024 Model Y Performance"

    def test_empty_config(self):
        assert build_vehicle_model({}) == ""


class TestMapVehicleData:
    def test_core_fields_mapped(self):
        vd = {
            "drive_state": {"latitude": 30.5, "longitude": -87.1, "speed": 12,
                            "heading": 90, "shift_state": "D"},
            "charge_state": {"battery_level": 64, "charging_state": "Charging",
                             "battery_range": 200},
            "vehicle_state": {"locked": True, "sentry_mode": True, "vehicle_name": "Tron"},
            "climate_state": {"is_climate_on": True, "inside_temp": 21},
        }
        d = map_vehicle_data(vd, _vehicle())
        assert d["latitude"] == 30.5 and d["longitude"] == -87.1
        assert d["speed"] == 12 and d["shift_state"] == "D"
        assert d["battery_level"] == 64 and d["charging_state"] == "Charging"
        assert d["locked"] is True and d["sentry_mode"] is True
        assert d["is_climate_on"] is True

    def test_defaults_when_sections_empty(self):
        d = map_vehicle_data({}, _vehicle())
        assert d["latitude"] is None and d["longitude"] is None
        assert d["speed"] == 0 and d["charging_state"] == "Disconnected"
        assert d["display_name"] == "Tron"
        assert d["vehicle_model"] == ""

    def test_includes_uid_and_model_and_timestamp(self):
        d = map_vehicle_data({"vehicle_config": {"car_type": "modely"}}, _vehicle())
        assert d["vehicle_model"] == "Model Y"
        assert d["UID"].startswith("TESLA-")
        assert isinstance(d["timestamp"], float)
