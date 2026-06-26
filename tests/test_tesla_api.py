"""Tests for teslaontarget.tesla_api.TeslaCoT (non-loop methods)."""
import dataclasses
import json
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget.tesla_api import TeslaCoT


@pytest.fixture
def cot(tmp_path, monkeypatch, make_config):
    monkeypatch.chdir(tmp_path)  # isolate all file writes to a temp cwd
    return TeslaCoT(make_config(), vehicle_id="VIN123", tak_client=MagicMock())


class TestInit:
    def test_uses_supplied_tak_client(self, cot):
        assert cot.vehicle_id == "VIN123"
        assert cot.positions_queue.maxlen == 2
        assert cot.debug_mode is False

    def test_creates_tak_client_when_none(self, tmp_path, monkeypatch, make_config):
        monkeypatch.chdir(tmp_path)
        with patch("teslaontarget.tesla_api.TAKClient") as TC:
            TeslaCoT(make_config(cot_url="tcp://1.2.3.4:9"))
            TC.assert_called_once_with("tcp://1.2.3.4:9")

    def test_debug_mode_makes_capture_dir(self, tmp_path, monkeypatch, make_config):
        monkeypatch.chdir(tmp_path)
        TeslaCoT(make_config(debug_mode=True), vehicle_id="v", tak_client=MagicMock())
        assert (tmp_path / "tesla_api_captures").is_dir()

    def test_debug_mode_without_vehicle_id(self, tmp_path, monkeypatch, make_config):
        monkeypatch.chdir(tmp_path)
        TeslaCoT(make_config(debug_mode=True), vehicle_id=None, tak_client=MagicMock())
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

    def test_zero_coordinate_is_valid(self, cot):
        # Regression: latitude 0.0 (equator) is a valid coordinate, not "missing".
        data = {"latitude": 0.0, "longitude": 0.0, "speed": 0}
        self._drive(cot, data, times=[1000, 1001, 1100], max_iters=2)
        cot.send_to_cot.assert_called_once()

    def test_none_coordinate_breaks(self, cot):
        # Only genuinely-missing coordinates (None) stop dead reckoning.
        data = {"latitude": None, "longitude": None, "speed": 0}
        self._drive(cot, data, times=[1000, 1001], max_iters=2)
        cot.send_to_cot.assert_not_called()


def _fake_vehicle(state="online", **extra):
    v = type("FakeVehicle", (dict,), {})(
        {"id_s": "3744443410507808", "id": 1, "display_name": "Tron", "state": state})
    v.get_vehicle_data = MagicMock()
    v.sync_wake_up = MagicMock()
    v._owner = MagicMock()
    for k, val in extra.items():
        setattr(v, k, val)
    return v


class TestClassifyApiError:
    @pytest.mark.parametrize("text,kind", [
        ("http 429 too many requests", "rate_limit"),
        ("read timeout occurred", "rate_limit"),
        ("vehicle unavailable", "unavailable"),
        ("vehicle is asleep", "unavailable"),
        ("something exploded", "other"),
    ])
    def test_classification(self, cot, text, kind):
        assert cot._classify_api_error(text) == kind


class TestHandleApiError:
    def test_rate_limit_backs_off_and_sends_cache(self, cot):
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1}
        delay = cot._handle_api_error(Exception("429 rate limit"))
        assert cot.rate_limit_backoff == 2
        assert delay == cot.config.api_loop_delay * 2
        cot.send_to_cot.assert_called_once()

    def test_unavailable_uses_cache(self, cot):
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1}
        delay = cot._handle_api_error(Exception("vehicle unavailable"))
        assert delay == cot.config.api_loop_delay
        cot.send_to_cot.assert_called_once()

    def test_unavailable_without_cache_warns(self, cot):
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = None
        cot._handle_api_error(Exception("asleep"))
        cot.send_to_cot.assert_not_called()

    def test_other_error_single(self, cot):
        delay = cot._handle_api_error(Exception("weird"))
        assert delay == cot.config.api_loop_delay
        assert cot.consecutive_errors == 1

    def test_other_error_escalates_after_three(self, cot):
        cot.consecutive_errors = 2
        delay = cot._handle_api_error(Exception("weird"))
        assert cot.consecutive_errors == 3
        assert delay > cot.config.api_loop_delay


class TestSeedAndWake:
    def test_wake_if_asleep_sends_wake(self, cot):
        v = _fake_vehicle(state="asleep")
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._wake_if_asleep(v)
        v.sync_wake_up.assert_called_once()

    def test_wake_skipped_when_online(self, cot):
        v = _fake_vehicle(state="online")
        cot._wake_if_asleep(v)
        v.sync_wake_up.assert_not_called()

    def test_wake_error_swallowed(self, cot):
        v = _fake_vehicle(state="asleep")
        v.sync_wake_up.side_effect = RuntimeError("nope")
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._wake_if_asleep(v)  # must not raise

    def test_fetch_initial_success(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = {"vin": "X"}
        assert cot._fetch_initial_data(v) == {"vin": "X"}

    def test_fetch_initial_all_fail(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.side_effect = Exception("fail")
        cot.max_wake_attempts = 2
        with patch("teslaontarget.tesla_api.time.sleep"):
            assert cot._fetch_initial_data(v) is None
        assert v.get_vehicle_data.call_count == 2

    def test_seed_no_data_no_cache_returns_false(self, cot):
        v = _fake_vehicle()
        cot.last_known_valid_data = None
        with patch.object(cot, "_fetch_initial_data", return_value=None):
            assert cot._seed_initial_position(v) is False

    def test_seed_no_data_with_cache_sends_and_proceeds(self, cot):
        v = _fake_vehicle()
        cot.last_known_valid_data = {"latitude": 1}
        cot.send_to_cot = MagicMock()
        with patch.object(cot, "_fetch_initial_data", return_value=None):
            assert cot._seed_initial_position(v) is True
        cot.send_to_cot.assert_called_once()

    def test_seed_with_gps_saves_position(self, cot):
        v = _fake_vehicle()
        vd = {"drive_state": {"latitude": 30.0, "longitude": -87.0}}
        with patch.object(cot, "_fetch_initial_data", return_value=vd):
            assert cot._seed_initial_position(v) is True
        assert cot.last_known_valid_data["latitude"] == 30.0


class TestDeadReckoningManagement:
    def test_start_when_moving(self, cot):
        cot.dead_reckoning_thread = None
        with patch("teslaontarget.tesla_api.threading.Thread") as T:
            cot._start_dead_reckoning({"speed": 30, "shift_state": "D"})
            T.assert_called_once()
            T.return_value.start.assert_called_once()

    def test_skip_when_parked(self, cot):
        cot.dead_reckoning_thread = None
        with patch("teslaontarget.tesla_api.threading.Thread") as T:
            cot._start_dead_reckoning({"speed": 0, "shift_state": "P"})
            T.assert_not_called()

    def test_restarts_existing_thread(self, cot):
        old = MagicMock()
        old.is_alive.return_value = True
        cot.dead_reckoning_thread = old
        with patch("teslaontarget.tesla_api.threading.Thread"):
            cot._start_dead_reckoning({"speed": 10, "shift_state": "D"})
        old.join.assert_called_once()


class TestPollOnce:
    def _vd_with_gps(self):
        return {"drive_state": {"latitude": 30.0, "longitude": -87.0, "speed": 5}}

    def test_valid_gps_path(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = self._vd_with_gps()
        cot._handle_valid_gps = MagicMock()
        cot._handle_missing_gps = MagicMock()
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._poll_once(v)
        cot._handle_valid_gps.assert_called_once()
        cot._handle_missing_gps.assert_not_called()

    def test_missing_gps_path(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = {"drive_state": {}}
        cot._handle_valid_gps = MagicMock()
        cot._handle_missing_gps = MagicMock()
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._poll_once(v)
        cot._handle_missing_gps.assert_called_once()

    def test_error_path_delegates_to_handler(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.side_effect = Exception("429 rate limit")
        with patch("teslaontarget.tesla_api.time.sleep") as slp:
            cot._poll_once(v)
        slp.assert_called_once()  # slept for the handler's backoff delay

    def test_backoff_reset_on_success(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = self._vd_with_gps()
        cot.consecutive_errors = 5
        cot.rate_limit_backoff = 8
        cot._handle_valid_gps = MagicMock()
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._poll_once(v)
        assert cot.consecutive_errors == 0 and cot.rate_limit_backoff == 1

    def test_zero_coordinates_count_as_valid_gps(self, cot):
        # Regression: lat=0.0 (equator) / lon=0.0 (prime meridian) are valid;
        # a truthiness check would wrongly treat them as "no GPS".
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = {"drive_state": {"latitude": 0.0, "longitude": 0.0}}
        cot._handle_valid_gps = MagicMock()
        cot._handle_missing_gps = MagicMock()
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._poll_once(v)
        cot._handle_valid_gps.assert_called_once()
        cot._handle_missing_gps.assert_not_called()


class TestHandleGps:
    def test_valid_gps_saves_sends_and_dr(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=True)
        cot.send_to_cot = MagicMock()
        cot._start_dead_reckoning = MagicMock()
        cot._handle_valid_gps({"latitude": 1, "longitude": 2, "speed": 9})
        assert cot.consecutive_no_gps_count == 0
        cot.send_to_cot.assert_called_once()
        cot._start_dead_reckoning.assert_called_once()

    def test_missing_gps_resends_cache(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=False)
        cot.dead_reckoning_thread = None
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1}
        cot._handle_missing_gps()
        assert cot.consecutive_no_gps_count == 1
        cot.send_to_cot.assert_called_once()

    def test_missing_gps_starts_dr_from_cache(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=True)
        cot.dead_reckoning_thread = None
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1, "speed": 20}
        with patch("teslaontarget.tesla_api.threading.Thread") as T:
            cot._handle_missing_gps()
            T.return_value.start.assert_called_once()

    def test_valid_gps_with_dr_disabled(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=False)
        cot.send_to_cot = MagicMock()
        cot._start_dead_reckoning = MagicMock()
        cot._handle_valid_gps({"latitude": 1, "longitude": 2})
        cot._start_dead_reckoning.assert_not_called()

    def test_missing_gps_thread_alive_skips_start(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=True)
        alive = MagicMock()
        alive.is_alive.return_value = True
        cot.dead_reckoning_thread = alive
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1}
        with patch("teslaontarget.tesla_api.threading.Thread") as T:
            cot._handle_missing_gps()
            T.assert_not_called()  # existing thread alive -> no new one
        cot.send_to_cot.assert_called_once()

    def test_missing_gps_dr_enabled_but_no_speed(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=True)
        cot.dead_reckoning_thread = None
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = {"latitude": 1, "speed": 0}  # not moving
        with patch("teslaontarget.tesla_api.threading.Thread") as T:
            cot._handle_missing_gps()
            T.assert_not_called()

    def test_missing_gps_no_cache_no_send(self, cot, monkeypatch):
        cot.config = dataclasses.replace(cot.config, dead_reckoning_enabled=False)
        cot.dead_reckoning_thread = None
        cot.send_to_cot = MagicMock()
        cot.last_known_valid_data = None
        cot._handle_missing_gps()
        cot.send_to_cot.assert_not_called()

    def test_seed_data_without_gps_proceeds(self, cot):
        v = _fake_vehicle()
        with patch.object(cot, "_fetch_initial_data", return_value={"drive_state": {}}):
            assert cot._seed_initial_position(v) is True  # no save, still proceeds


class TestPollOnceExtra:
    def test_poll_warns_on_missing_autopilot_while_driving(self, cot):
        v = _fake_vehicle()
        v.get_vehicle_data.return_value = {
            "drive_state": {"latitude": 30.0, "longitude": -87.0, "shift_state": "D"},
            "vehicle_state": {"autopilot_state": None},  # explicitly unavailable
        }
        cot._handle_valid_gps = MagicMock()
        with patch("teslaontarget.tesla_api.time.sleep"):
            cot._poll_once(v)  # exercises the autopilot-unavailable warning
