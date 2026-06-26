"""Tests for teslaontarget.tesla_api.TeslaCoT (non-loop methods)."""
import json
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget.config_handler import Config
from teslaontarget.tesla_api import TeslaCoT


@pytest.fixture
def cot(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)  # isolate all file writes to a temp cwd
    monkeypatch.setattr(Config, "COT_URL", "tcp://h:1", raising=False)
    monkeypatch.setattr(Config, "DEBUG_MODE", False, raising=False)
    monkeypatch.setattr(Config, "LAST_POSITION_FILE", "last.json", raising=False)
    monkeypatch.setattr(Config, "API_LOOP_DELAY", 10, raising=False)
    monkeypatch.setattr(Config, "DEAD_RECKONING_DELAY", 1, raising=False)
    monkeypatch.setattr(Config, "MPH_TO_MS", 0.44704, raising=False)
    return TeslaCoT(vehicle_id="VIN123", tak_client=MagicMock())


class TestInit:
    def test_uses_supplied_tak_client(self, cot):
        assert cot.vehicle_id == "VIN123"
        assert cot.positions_queue.maxlen == 2
        assert cot.debug_mode is False

    def test_creates_tak_client_when_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Config, "COT_URL", "tcp://1.2.3.4:9", raising=False)
        monkeypatch.setattr(Config, "DEBUG_MODE", False, raising=False)
        with patch("teslaontarget.tesla_api.TAKClient") as TC:
            TeslaCoT(vehicle_id="v")
            TC.assert_called_once_with("tcp://1.2.3.4:9")

    def test_debug_mode_makes_capture_dir(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Config, "DEBUG_MODE", True, raising=False)
        TeslaCoT(vehicle_id="v", tak_client=MagicMock())
        assert (tmp_path / "tesla_api_captures").is_dir()

    def test_debug_mode_without_vehicle_id(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        monkeypatch.setattr(Config, "DEBUG_MODE", True, raising=False)
        monkeypatch.setattr(Config, "LAST_POSITION_FILE", "last.json", raising=False)
        TeslaCoT(vehicle_id=None, tak_client=MagicMock())  # debug on, no id -> no log
        assert (tmp_path / "tesla_api_captures").is_dir()


class TestPositionFilename:
    def test_sanitizes_vehicle_id(self, cot):
        cot.vehicle_id = "5YJ/3*E1!a"
        assert cot._get_position_filename() == "last_position_5YJ3E1a.json"

    def test_falls_back_to_config_when_no_id(self, cot):
        cot.vehicle_id = None
        assert cot._get_position_filename() == "last.json"


class TestPositionIO:
    def test_save_then_read_roundtrip(self, cot):
        cot.save_last_position_to_file({"latitude": 1.0})
        assert cot.read_last_position_from_file() == {"latitude": 1.0}

    def test_read_missing_returns_none(self, cot):
        cot.position_file = "does_not_exist.json"
        assert cot.read_last_position_from_file() is None

    def test_save_error_is_logged_not_raised(self, cot):
        with patch("teslaontarget.tesla_api.save_json_file", side_effect=OSError("x")):
            cot.save_last_position_to_file({"a": 1})  # must not raise


class TestDebugCapture:
    def test_noop_when_debug_disabled(self, cot, tmp_path):
        cot.debug_mode = False
        cot.save_debug_capture({"a": 1})
        assert not (tmp_path / "tesla_api_captures").exists()

    def test_writes_capture_when_enabled(self, cot, tmp_path):
        import os
        cot.debug_mode = True
        cot.debug_dir = str(tmp_path / "caps")
        os.makedirs(cot.debug_dir, exist_ok=True)
        cot.save_debug_capture({"vin": "X"}, prefix="probe")
        files = list((tmp_path / "caps").glob("probe_*.json"))
        assert len(files) == 1
        body = json.loads(files[0].read_text())
        assert body["raw_api_response"] == {"vin": "X"}
        assert cot.capture_count == 1

    def test_write_error_is_swallowed(self, cot):
        cot.debug_mode = True
        cot.debug_dir = "/nonexistent_root_dir_xyz"
        cot.save_debug_capture({"a": 1})  # must not raise


class TestSendToCot:
    def test_success_path(self, cot):
        cot.tak_client.send_cot.return_value = True
        cot.send_to_cot({"display_name": "Tron", "latitude": 1, "longitude": 2})
        cot.tak_client.send_cot.assert_called_once()

    def test_failed_send_warns_no_raise(self, cot):
        cot.tak_client.send_cot.return_value = False
        cot.send_to_cot({"latitude": 1, "longitude": 2})

    def test_generation_error_is_caught(self, cot):
        with patch("teslaontarget.tesla_api.generate_cot_packet", side_effect=ValueError("boom")):
            cot.send_to_cot({"latitude": 1})  # must not raise


def _vehicle(**over):
    base = {"id_s": "3744443410507808", "display_name": "Tron"}
    base.update(over)
    return base


class TestExtractRelevantData:
    def test_uid_is_stable_md5(self, cot):
        import hashlib
        d = cot.extract_relevant_data({}, _vehicle())
        assert d["UID"] == "TESLA-" + hashlib.md5(b"3744443410507808").hexdigest()[:8]

    def test_core_fields_mapped(self, cot):
        vd = dict(
            drive_state={"latitude": 30.5, "longitude": -87.1, "speed": 12,
                         "heading": 90, "shift_state": "D"},
            charge_state={"battery_level": 64, "charging_state": "Charging",
                          "battery_range": 200},
            vehicle_state={"locked": True, "sentry_mode": True, "vehicle_name": "Tron"},
            climate_state={"is_climate_on": True, "inside_temp": 21},
        )
        d = cot.extract_relevant_data(vd, _vehicle())
        assert d["latitude"] == 30.5 and d["longitude"] == -87.1
        assert d["speed"] == 12 and d["shift_state"] == "D"
        assert d["battery_level"] == 64 and d["charging_state"] == "Charging"
        assert d["locked"] is True and d["sentry_mode"] is True
        assert d["is_climate_on"] is True

    def test_defaults_when_sections_empty(self, cot):
        d = cot.extract_relevant_data({}, _vehicle())
        assert d["latitude"] is None and d["longitude"] is None
        assert d["speed"] == 0 and d["charging_state"] == "Disconnected"
        assert d["display_name"] == "Tron"
        assert d["vehicle_model"] == ""  # no car_type

    @pytest.mark.parametrize("car_type,expected", [
        ("models", "Model S"), ("modelx", "Model X"), ("model3", "Model 3"),
        ("modely", "Model Y"), ("cybertruck", "Cybertruck"),
        ("roadster", "roadster"),  # unmapped -> passthrough
    ])
    def test_model_name_mapping(self, cot, car_type, expected):
        d = cot.extract_relevant_data({"vehicle_config": {"car_type": car_type}}, _vehicle())
        assert d["vehicle_model"] == expected

    def test_trim_performance_variant(self, cot):
        d = cot.extract_relevant_data(
            {"vehicle_config": {"car_type": "modely", "trim_badging": "p74d"}}, _vehicle())
        assert d["vehicle_model"] == "Model Y Performance"

    def test_trim_long_range_variant(self, cot):
        d = cot.extract_relevant_data(
            {"vehicle_config": {"car_type": "model3", "trim_badging": "ld"}}, _vehicle())
        assert d["vehicle_model"] == "Model 3 Long Range"

    def test_trim_other_uppercased(self, cot):
        d = cot.extract_relevant_data(
            {"vehicle_config": {"car_type": "models", "trim_badging": "xx"}}, _vehicle())
        assert d["vehicle_model"] == "Model S XX"

    def test_year_prefixed(self, cot):
        d = cot.extract_relevant_data(
            {"vehicle_config": {"car_type": "modely", "trim_badging": "p", "year": 2024}},
            _vehicle())
        assert d["vehicle_model"] == "2024 Model Y Performance"

    def test_vehicle_id_fallback_key(self, cot):
        import hashlib
        v = {"vehicle_id": "987", "display_name": "X"}  # no id_s
        d = cot.extract_relevant_data({}, v)
        assert d["UID"] == "TESLA-" + hashlib.md5(b"987").hexdigest()[:8]


class TestDeadReckoning:
    def _drive(self, cot, initial_data, times, max_iters=2):
        """Run dead_reckoning_update with a controlled clock + bounded loop."""
        cot.send_to_cot = MagicMock()
        cot.stop_dead_reckoning = MagicMock()
        cot.stop_dead_reckoning.is_set.side_effect = [False] * (max_iters - 1) + [True]
        with patch("teslaontarget.tesla_api.time") as t:
            t.time.side_effect = times
            t.sleep = MagicMock()
            cot.dead_reckoning_update(initial_data)
        return cot

    def test_stationary_resends_same_position(self, cot):
        data = {"latitude": 30.0, "longitude": -87.0, "speed": 0}
        # start=1000, timestamp=1001, break-check=1100 (>=9 -> break)
        self._drive(cot, data, times=[1000, 1001, 1100])
        cot.send_to_cot.assert_called_once()
        sent = cot.send_to_cot.call_args[0][0]
        assert sent["latitude"] == 30.0 and sent["dead_reckoned"] is True

    def test_speed_none_treated_as_stationary(self, cot):
        data = {"latitude": 30.0, "longitude": -87.0, "speed": None}
        self._drive(cot, data, times=[1000, 1001, 1100])
        cot.send_to_cot.assert_called_once()

    def test_moving_advances_position(self, cot):
        data = {"latitude": 30.0, "longitude": -87.0, "speed": 60, "heading": 90}
        self._drive(cot, data, times=[1000, 1001, 1100])
        sent = cot.send_to_cot.call_args[0][0]
        # heading 90 (east) -> longitude moves, latitude ~unchanged
        assert sent["dead_reckoned"] is True
        assert sent["longitude"] != -87.0

    def test_continues_until_stop_when_under_max_duration(self, cot):
        data = {"latitude": 30.0, "longitude": -87.0, "speed": 0}
        # break-check 1002-1000=2 < 9 -> no break -> next is_set True -> exit
        self._drive(cot, data, times=[1000, 1001, 1002], max_iters=2)
        cot.send_to_cot.assert_called_once()

    def test_moving_with_none_heading_and_no_break(self, cot):
        # heading None -> 0; time under max_duration so it loops to the stop event
        data = {"latitude": 30.0, "longitude": -87.0, "speed": 60, "heading": None}
        self._drive(cot, data, times=[1000, 1001, 1002], max_iters=2)
        cot.send_to_cot.assert_called_once()

    def test_zero_coordinate_breaks_immediately(self, cot):
        # latitude 0 formats fine for the log but is falsy -> "no valid position"
        data = {"latitude": 0, "longitude": -87.0, "speed": 0}
        # max_iters=2 so the loop body runs once and hits the else/break
        self._drive(cot, data, times=[1000, 1001], max_iters=2)
        cot.send_to_cot.assert_not_called()
