"""Tests for teslaontarget.cot — CoT XML generation from vehicle data."""
import xml.etree.ElementTree as ET

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st

# Robust under mutmut/coverage instrumentation: no deadline, and allow the
# class-method test to be driven by different executors across mutation runs.
_PROP = settings(deadline=None, suppress_health_check=[HealthCheck.differing_executors])

from teslaontarget.cot import (
    generate_cot_packet,
    format_cot_for_tak,
    celsius_to_fahrenheit,
)


def _parse(data):
    root = ET.fromstring(generate_cot_packet(data))
    return root


def _remarks(data):
    return _parse(data).find("./detail/remarks").text


class TestEventSkeleton:
    def test_defaults_for_empty_data(self):
        root = _parse({})
        assert root.tag == "event"
        assert root.get("uid") == "Tesla-Unknown"
        assert root.get("type") == "a-f-G-E-V-C"
        assert root.get("how") == "m-g"
        pt = root.find("point")
        assert pt.get("lat") == "0"
        assert pt.get("lon") == "0"
        assert pt.get("ce") == "12.5"  # stationary default
        assert root.find("./detail/contact").get("callsign") == "Tesla"
        assert root.find("./detail/takv").get("device") == "TESLA Model"

    def test_uid_and_callsign_and_model_used(self):
        root = _parse({"UID": "TESLA-abc", "display_name": "Tron",
                       "vehicle_model": "Model Y"})
        assert root.get("uid") == "TESLA-abc"
        assert root.find("./detail/contact").get("callsign") == "Tron"
        assert root.find("./detail/uid").get("Droid") == "Tron"
        assert root.find("./detail/takv").get("device") == "TESLA Model Y"

    def test_lat_lon_passed_through(self):
        pt = _parse({"latitude": 30.5, "longitude": -87.1}).find("point")
        assert pt.get("lat") == "30.5"
        assert pt.get("lon") == "-87.1"

    def test_stale_is_five_minutes_after_start(self):
        from datetime import datetime
        root = _parse({})
        fmt = "%Y-%m-%dT%H:%M:%S.%fZ"
        start = datetime.strptime(root.get("start"), fmt)
        stale = datetime.strptime(root.get("stale"), fmt)
        assert abs((stale - start).total_seconds() - 300) < 2


class TestPointAndTrack:
    def test_moving_uses_tight_circular_error(self):
        assert _parse({"speed": 50}).find("point").get("ce") == "5.0"

    def test_slow_uses_loose_circular_error(self):
        assert _parse({"speed": 1}).find("point").get("ce") == "12.5"

    def test_elevation_none_becomes_zero(self):
        assert _parse({"elevation": None}).find("point").get("hae") == "0.000"

    def test_elevation_value_formatted(self):
        assert _parse({"elevation": 12.3456}).find("point").get("hae") == "12.346"

    def test_heading_none_becomes_zero(self):
        assert _parse({"heading": None}).find("./detail/track").get("course") == "0.00000000"

    def test_speed_none_becomes_zero_ms(self):
        assert _parse({"speed": None}).find("./detail/track").get("speed") == "0.00000000"

    def test_speed_converted_mph_to_ms(self):
        course = _parse({"speed": 100}).find("./detail/track").get("speed")
        assert float(course) == pytest.approx(44.704)

    def test_battery_level_int_cast(self):
        assert _parse({"battery_level": 87.9}).find("./detail/status").get("battery") == "87"


class TestRemarks:
    def test_gear_default_when_falsy(self):
        assert "Gear: P" in _remarks({"shift_state": ""})

    def test_gear_value_shown(self):
        assert "Gear: D" in _remarks({"shift_state": "D"})

    def test_range_shown_when_present(self):
        assert "Range: 165 mi" in _remarks({"battery_range": 165.4})

    def test_range_absent_when_none(self):
        assert "Range:" not in _remarks({"battery_range": None})

    def test_charging_with_hours_and_minutes(self):
        r = _remarks({"charging_state": "Charging", "minutes_to_full_charge": 95,
                      "charge_limit_soc": 90})
        assert "Charging" in r and "(1h 35m to 90%)" in r

    def test_charging_with_minutes_only(self):
        r = _remarks({"charging_state": "Charging", "minutes_to_full_charge": 40})
        assert "(40m to 80%)" in r  # default charge_limit_soc 80

    def test_charging_time_to_full_hours(self):
        r = _remarks({"charging_state": "Charging", "minutes_to_full_charge": 0,
                      "time_to_full_charge": 2.5})
        assert "(2.5h to 80%)" in r

    def test_charging_time_to_full_sub_hour(self):
        r = _remarks({"charging_state": "Charging", "minutes_to_full_charge": 0,
                      "time_to_full_charge": 0.5})
        assert "(30m to 80%)" in r

    def test_charge_port_open_note(self):
        r = _remarks({"charging_state": "Charging", "charge_port_door_open": True})
        assert "Port Open" in r

    @pytest.mark.parametrize("state", ["Disconnected", "Complete", None])
    def test_no_charging_block_when_not_charging(self, state):
        assert "to 80%" not in _remarks({"charging_state": state})

    @pytest.mark.parametrize("ap,expected", [(2, "AUTOPILOT ACTIVE"),
                                             (3, "FSD ACTIVE"),
                                             (1, "AUTOPILOT AVAILABLE")])
    def test_autopilot_states_when_driving(self, ap, expected):
        assert expected in _remarks({"shift_state": "D", "autopilot_state": ap})

    def test_no_autopilot_when_parked(self):
        assert "AUTOPILOT" not in _remarks({"shift_state": "P", "autopilot_state": 2})

    def test_driving_unknown_autopilot_state_adds_nothing(self):
        # truthy autopilot_state that is not 1/2/3 -> no AP/FSD text appended
        r = _remarks({"shift_state": "D", "autopilot_state": 4})
        assert "AUTOPILOT" not in r and "FSD" not in r

    def test_climate_on(self):
        assert "Climate: ON" in _remarks({"is_climate_on": True})

    def test_parked_security_block(self):
        r = _remarks({"shift_state": "P", "sentry_mode": True, "locked": True})
        assert "Sentry: ON" in r and "Doors: Locked" in r

    def test_parked_unlocked_sentry_off(self):
        r = _remarks({"shift_state": "P", "sentry_mode": False, "locked": False})
        assert "Sentry: OFF" in r and "Doors: Unlocked" in r

    def test_locked_none_omits_doors(self):
        assert "Doors:" not in _remarks({"shift_state": "P", "locked": None})

    def test_windows_frunk_trunk_open_alerts(self):
        r = _remarks({"shift_state": "P", "fd_window": 1, "rp_window": 1,
                      "ft": 1, "rt": 1})
        assert "WINDOWS OPEN: FD,RP" in r
        assert "FRUNK OPEN" in r and "TRUNK OPEN" in r

    def test_shift_state_none_enters_security_block(self):
        # shift_state explicitly None -> "Gear: P" and security block both apply.
        r = _remarks({"shift_state": None, "sentry_mode": True})
        assert "Gear: P" in r and "Sentry: ON" in r

    def test_none_window_and_trunk_fields_do_not_crash(self):
        # Regression: Tesla's vehicle_state can return null for window/trunk
        # fields; extract_relevant_data passes them straight through, so
        # `None > 0` would raise TypeError mid-packet and drop the send.
        r = _remarks({"shift_state": "P", "fd_window": None, "fp_window": None,
                      "rd_window": None, "rp_window": None, "ft": None, "rt": None})
        assert "WINDOWS OPEN" not in r
        assert "FRUNK OPEN" not in r and "TRUNK OPEN" not in r


class TestFormatForTak:
    def test_prepends_xml_declaration_and_returns_bytes(self):
        out = format_cot_for_tak("<event/>")
        assert isinstance(out, bytes)
        assert out.startswith(b"<?xml version='1.0' encoding='UTF-8' standalone='yes'?>")
        assert out.endswith(b"<event/>")

    def test_roundtrip_with_generated_packet(self):
        out = format_cot_for_tak(generate_cot_packet({"UID": "X"}))
        # strip declaration, remainder must parse
        body = out.split(b"?>", 1)[1]
        assert ET.fromstring(body).get("uid") == "X"


class TestCelsiusToFahrenheit:
    def test_none(self):
        assert celsius_to_fahrenheit(None) is None

    @pytest.mark.parametrize("c,f", [(0, 32), (100, 212), (-40, -40)])
    def test_known(self, c, f):
        assert celsius_to_fahrenheit(c) == f


class TestProperties:
    _data = st.fixed_dictionaries({
        "latitude": st.floats(-90, 90, allow_nan=False),
        "longitude": st.floats(-180, 180, allow_nan=False),
        "speed": st.floats(0, 200, allow_nan=False),
        "heading": st.floats(0, 360, allow_nan=False),
        "battery_level": st.integers(0, 100),
        "shift_state": st.sampled_from(["P", "D", "R", "N", "", None]),
        "sentry_mode": st.booleans(),
        "locked": st.sampled_from([True, False, None]),
        "battery_range": st.one_of(st.none(), st.floats(0, 400, allow_nan=False)),
        "charging_state": st.sampled_from(["Charging", "Disconnected", "Complete", None]),
    })

    @_PROP
    @given(_data)
    def test_always_emits_parseable_xml(self, data):
        root = ET.fromstring(generate_cot_packet(data))
        assert root.tag == "event"
        # lat/lon round-trip into the point element
        assert root.find("point").get("lat") == str(data["latitude"])
        assert root.find("point").get("lon") == str(data["longitude"])
        # remarks always present and non-empty
        assert root.find("./detail/remarks").text
