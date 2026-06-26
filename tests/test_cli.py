"""Tests for teslaontarget.cli (entry point, fully mocked)."""
import logging
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget import cli
from teslaontarget.config_handler import Config


def test_main_module_is_importable():
    # Covers teslaontarget/__main__.py (the `python -m teslaontarget` shim).
    # __name__ != "__main__" here, so main() is not invoked, only the import runs.
    import teslaontarget.__main__ as entry
    assert entry.main is not None


class TestSignalHandler:
    def test_sets_running_false(self, monkeypatch):
        monkeypatch.setattr(cli, "running", True)
        cli.signal_handler(2, None)
        assert cli.running is False


class TestLogHandlers:
    def test_default_adds_file_handler(self):
        with patch("teslaontarget.cli.logging.FileHandler") as FH:
            handlers = cli._make_log_handlers()
        assert len(handlers) == 2  # stream + file
        FH.assert_called_once_with("teslaontarget.log")

    def test_uses_logs_dir_when_writable(self):
        with patch("teslaontarget.cli.os.path.exists", return_value=True), \
             patch("teslaontarget.cli.os.access", return_value=True), \
             patch("teslaontarget.cli.logging.FileHandler") as FH:
            cli._make_log_handlers()
        FH.assert_called_once_with("/logs/teslaontarget.log")

    def test_file_handler_error_falls_back_to_stdout(self, capsys):
        with patch("teslaontarget.cli.logging.FileHandler", side_effect=OSError("ro")):
            handlers = cli._make_log_handlers()
        assert len(handlers) == 1  # stream only
        assert "Unable to create log file" in capsys.readouterr().out


class TestParseAndConfig:
    def test_parse_args(self):
        with patch("sys.argv", ["prog", "--debug", "--config", "/x/config.py"]):
            args = cli._parse_args()
        assert args.debug is True and args.config == "/x/config.py"

    def test_load_valid_config(self, monkeypatch):
        monkeypatch.setattr(Config, "load_from_file", MagicMock())
        monkeypatch.setattr(Config, "validate", MagicMock(return_value=True))
        cli._load_and_validate_config(MagicMock(debug=False))

    def test_debug_flag_sets_level(self, monkeypatch):
        monkeypatch.setattr(Config, "load_from_file", MagicMock())
        monkeypatch.setattr(Config, "validate", MagicMock(return_value=True))
        cli._load_and_validate_config(MagicMock(debug=True))
        assert logging.getLogger().level == logging.DEBUG

    def test_invalid_config_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "load_from_file", MagicMock())
        monkeypatch.setattr(Config, "validate", MagicMock(return_value=False))
        with pytest.raises(SystemExit):
            cli._load_and_validate_config(MagicMock(debug=False))


class TestSelectVehicles:
    def test_no_vehicles_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "VEHICLE_FILTER", [], raising=False)
        tesla = MagicMock()
        tesla.vehicle_list.return_value = []
        with pytest.raises(SystemExit):
            cli._select_vehicles(tesla)

    def test_no_filter_returns_all(self, monkeypatch):
        monkeypatch.setattr(Config, "VEHICLE_FILTER", [], raising=False)
        tesla = MagicMock()
        tesla.vehicle_list.return_value = [{"display_name": "A"}, {"display_name": "B"}]
        assert len(cli._select_vehicles(tesla)) == 2

    def test_filter_matches_subset(self, monkeypatch):
        monkeypatch.setattr(Config, "VEHICLE_FILTER", ["Tron"], raising=False)
        tesla = MagicMock()
        tesla.vehicle_list.return_value = [
            {"display_name": "Tron", "vin": "1"}, {"display_name": "Other", "vin": "2"}]
        result = cli._select_vehicles(tesla)
        assert len(result) == 1 and result[0]["display_name"] == "Tron"

    def test_filter_no_match_exits(self, monkeypatch):
        monkeypatch.setattr(Config, "VEHICLE_FILTER", ["Nope"], raising=False)
        tesla = MagicMock()
        tesla.vehicle_list.return_value = [{"display_name": "Tron", "vin": "1"}]
        with pytest.raises(SystemExit):
            cli._select_vehicles(tesla)


class TestBuildHealthMonitor:
    def test_uses_defaults_when_unset(self, monkeypatch):
        for attr in ("HEALTH_NO_SEND_SECONDS", "HEALTH_CHECK_INTERVAL", "HEALTH_HARD_RESTART_SECONDS"):
            monkeypatch.setattr(Config, attr, 0, raising=False)
        monkeypatch.setattr(Config, "API_LOOP_DELAY", 10, raising=False)
        with patch("teslaontarget.cli.HealthMonitor") as HM:
            cli._build_health_monitor(MagicMock())
        kw = HM.call_args.kwargs
        assert kw["max_no_send_seconds"] == 120  # max(120, 10*8)
        assert kw["check_interval"] == 15
        assert kw["hard_restart_seconds"] == 600

    def test_uses_configured_values(self, monkeypatch):
        monkeypatch.setattr(Config, "HEALTH_NO_SEND_SECONDS", 300, raising=False)
        monkeypatch.setattr(Config, "HEALTH_CHECK_INTERVAL", 30, raising=False)
        monkeypatch.setattr(Config, "HEALTH_HARD_RESTART_SECONDS", 999, raising=False)
        monkeypatch.setattr(Config, "API_LOOP_DELAY", 10, raising=False)
        with patch("teslaontarget.cli.HealthMonitor") as HM:
            cli._build_health_monitor(MagicMock())
        kw = HM.call_args.kwargs
        assert kw["max_no_send_seconds"] == 300 and kw["hard_restart_seconds"] == 999


class TestWakeVehicles:
    def test_wakes_asleep_only(self):
        a = _vmock("asleep")
        b = _vmock("online")
        cli._wake_vehicles([a, b])
        a.sync_wake_up.assert_called_once()
        b.sync_wake_up.assert_not_called()

    def test_wake_error_swallowed(self):
        a = _vmock("asleep")
        a.sync_wake_up.side_effect = RuntimeError("x")
        cli._wake_vehicles([a])  # must not raise


def _vmock(state):
    data = {"state": state, "display_name": "Car"}
    m = MagicMock()
    m.get.side_effect = data.get
    m.__getitem__ = lambda s, k: data[k]
    return m


class TestStartTracking:
    def test_spawns_one_thread_per_vehicle(self, monkeypatch):
        monkeypatch.setattr(Config, "COT_URL", "tcp://h:1", raising=False)
        v = _vmock("online")
        v.get.side_effect = {"vin": "VIN1", "display_name": "Car", "state": "online"}.get
        with patch("teslaontarget.cli.TeslaCoT"), \
             patch("teslaontarget.cli.threading.Thread") as T:
            threads = cli._start_tracking_threads([v], MagicMock())
        assert len(threads) == 1
        T.return_value.start.assert_called_once()


class TestMonitorThreads:
    def test_runs_one_pass_then_stops(self, monkeypatch):
        monkeypatch.setattr(cli, "running", True)
        monkeypatch.setattr(Config, "API_LOOP_DELAY", 10, raising=False)
        t_alive = MagicMock()
        t_alive.is_alive.return_value = True
        t_dead = MagicMock()
        t_dead.is_alive.return_value = False

        def stop(_):
            cli.running = False
        with patch("teslaontarget.cli.time.sleep", side_effect=stop):
            cli._monitor_threads([t_alive, t_dead])  # alive_count 1 < 2 -> warning
        assert cli.running is False

    def test_all_alive_no_warning(self, monkeypatch):
        monkeypatch.setattr(cli, "running", True)
        monkeypatch.setattr(Config, "API_LOOP_DELAY", 10, raising=False)
        t1 = MagicMock()
        t1.is_alive.return_value = True
        t2 = MagicMock()
        t2.is_alive.return_value = True

        def stop(_):
            cli.running = False
        with patch("teslaontarget.cli.time.sleep", side_effect=stop):
            cli._monitor_threads([t1, t2])  # alive_count 2 == 2 -> no warning branch
        assert cli.running is False


class TestMain:
    def _patch_all(self):
        from unittest.mock import DEFAULT
        return patch.multiple(
            "teslaontarget.cli",
            _parse_args=DEFAULT, _load_and_validate_config=DEFAULT, Tesla=DEFAULT,
            _select_vehicles=DEFAULT, TAKClient=DEFAULT, _build_health_monitor=DEFAULT,
            _wake_vehicles=DEFAULT, _start_tracking_threads=DEFAULT,
            _monitor_threads=DEFAULT, signal=DEFAULT,
        )

    @staticmethod
    def _prime(m):
        m["_parse_args"].return_value = MagicMock(debug=False, config=None)
        m["_select_vehicles"].return_value = [{"display_name": "A"}]
        m["_start_tracking_threads"].return_value = []

    def test_happy_path_starts_and_stops_health(self):
        with self._patch_all() as m:
            self._prime(m)
            cli.main()
            m["_build_health_monitor"].return_value.start.assert_called_once()
            m["_build_health_monitor"].return_value.stop.assert_called_once()

    def test_keyboard_interrupt_is_handled(self):
        with self._patch_all() as m:
            self._prime(m)
            m["_monitor_threads"].side_effect = KeyboardInterrupt()
            cli.main()  # must not raise

    def test_fatal_error_exits(self):
        with self._patch_all() as m:
            self._prime(m)
            m["_select_vehicles"].side_effect = RuntimeError("boom")
            with pytest.raises(SystemExit):
                cli.main()

    def test_finally_swallows_health_stop_error(self):
        with self._patch_all() as m:
            self._prime(m)
            m["_build_health_monitor"].return_value.stop.side_effect = RuntimeError("x")
            cli.main()  # finally must not raise
