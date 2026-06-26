"""Tests for teslaontarget.health.HealthMonitor."""
import json
import time
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget.health import HealthMonitor


def _client(**snapshot):
    c = MagicMock()
    c.health_snapshot.return_value = snapshot
    return c


@pytest.fixture
def monitor(tmp_path):
    return HealthMonitor(
        _client(connected=True, last_send_ok=time.time()),
        health_file=str(tmp_path / "health.json"),
        max_no_send_seconds=100,
        check_interval=1,
        hard_restart_seconds=500,
    )


class TestInit:
    def test_hard_restart_defaults_to_five_times(self):
        m = HealthMonitor(MagicMock(), max_no_send_seconds=120, hard_restart_seconds=None)
        assert m.hard_restart_seconds == 600

    def test_hard_restart_explicit(self):
        m = HealthMonitor(MagicMock(), max_no_send_seconds=120, hard_restart_seconds=999)
        assert m.hard_restart_seconds == 999


class TestStaleness:
    def test_none_when_never_sent(self, monitor):
        assert monitor._staleness(1000.0, None) is None

    def test_seconds_since_last_ok(self, monitor):
        assert monitor._staleness(1000.0, 940.0) == 60

    def test_never_negative(self, monitor):
        # clock skew: last_ok in the future -> clamped to 0
        assert monitor._staleness(1000.0, 1005.0) == 0


class TestWriteSnapshot:
    def test_writes_atomically(self, tmp_path):
        path = tmp_path / "h.json"
        m = HealthMonitor(MagicMock(), health_file=str(path))
        m._write_snapshot({"a": 1})
        assert json.loads(path.read_text()) == {"a": 1}
        assert not (tmp_path / "h.json.tmp").exists()  # tmp renamed away

    def test_write_failure_is_swallowed(self, tmp_path):
        m = HealthMonitor(MagicMock(), health_file=str(tmp_path / "missing" / "h.json"))
        m._write_snapshot({"a": 1})  # parent dir missing -> caught, no raise


class TestCheckOnce:
    def test_fresh_send_no_action(self, tmp_path):
        client = _client(connected=True, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=500)
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=1050.0)  # only 50s stale
        client.disconnect.assert_not_called()
        client.start_background_reconnect.assert_not_called()
        ex.assert_not_called()
        snap = json.loads((tmp_path / "h.json").read_text())
        assert snap["stale_seconds"] == 50

    def test_stale_forces_reconnect(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=5000)
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=1200.0)  # 200s stale > 100
        client.disconnect.assert_called_once()
        client.start_background_reconnect.assert_called_once()
        ex.assert_not_called()

    def test_disconnect_error_swallowed_still_reconnects(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        client.disconnect.side_effect = RuntimeError("boom")
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=5000)
        with patch("teslaontarget.health.os._exit"):
            m._check_once(now=1200.0)
        client.start_background_reconnect.assert_called_once()

    def test_critical_staleness_exits(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=500)
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=2000.0)  # 1000s stale > 500
            ex.assert_called_once_with(12)

    def test_never_sent_no_action(self, tmp_path):
        client = _client(connected=True, last_send_ok=None)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100)
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=9999.0)
        client.disconnect.assert_not_called()
        ex.assert_not_called()

    def test_client_without_snapshot_method(self, tmp_path):
        client = MagicMock(spec=[])  # no health_snapshot attribute
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"))
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=1000.0)
        ex.assert_not_called()
        snap = json.loads((tmp_path / "h.json").read_text())
        assert snap["tak"] == {}

    def test_no_hard_restart_when_threshold_none(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100)
        m.hard_restart_seconds = None  # disable escalation
        with patch("teslaontarget.health.os._exit") as ex:
            m._check_once(now=99999.0)
        ex.assert_not_called()


class TestAlerting:
    def test_alert_noop_when_no_url(self):
        m = HealthMonitor(MagicMock(), alert_url="")
        with patch("teslaontarget.health.urllib.request.urlopen") as uo:
            m._alert("hi")
        uo.assert_not_called()

    def test_alert_posts_message_to_url(self):
        m = HealthMonitor(MagicMock(), alert_url="https://ntfy.sh/tot")
        with patch("teslaontarget.health.urllib.request.urlopen") as uo:
            m._alert("stale!")
        uo.assert_called_once()
        req = uo.call_args[0][0]
        assert req.full_url == "https://ntfy.sh/tot"
        assert req.data == b"stale!"

    def test_alert_error_is_swallowed(self):
        m = HealthMonitor(MagicMock(), alert_url="https://x")
        with patch("teslaontarget.health.urllib.request.urlopen", side_effect=OSError("net")):
            m._alert("x")  # must not raise

    def test_alert_fired_once_per_stale_episode(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=5000,
                          alert_url="https://x")
        with patch("teslaontarget.health.os._exit"), patch.object(m, "_alert") as alert:
            m._check_once(now=1200.0)  # 200s stale -> alert
            m._check_once(now=1300.0)  # still stale -> deduped
        alert.assert_called_once()

    def test_alert_rearms_after_recovery(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=5000,
                          alert_url="https://x")
        with patch("teslaontarget.health.os._exit"), patch.object(m, "_alert") as alert:
            m._check_once(now=1200.0)  # stale -> alert #1
            client.health_snapshot.return_value = {"connected": True, "last_send_ok": 1300.0}
            m._check_once(now=1310.0)  # healthy -> re-arm
            client.health_snapshot.return_value = {"connected": False, "last_send_ok": 1300.0}
            m._check_once(now=1500.0)  # stale again -> alert #2
        assert alert.call_count == 2

    def test_critical_sends_alert_then_exits(self, tmp_path):
        client = _client(connected=False, last_send_ok=1000.0)
        m = HealthMonitor(client, health_file=str(tmp_path / "h.json"),
                          max_no_send_seconds=100, hard_restart_seconds=500,
                          alert_url="https://x")
        with patch("teslaontarget.health.os._exit") as ex, patch.object(m, "_alert") as alert:
            m._check_once(now=2000.0)  # 1000s stale > 500 critical
        ex.assert_called_once_with(12)
        assert alert.call_count == 2  # stale warning + critical


class TestThreadLifecycle:
    def test_start_then_stop(self, monitor):
        with patch("teslaontarget.health.os._exit"):
            monitor.check_interval = 0.02
            monitor.start()
            assert monitor._thread.is_alive()
            time.sleep(0.05)
            monitor.stop()
        assert not monitor._thread.is_alive()

    def test_start_is_idempotent(self, monitor):
        with patch("teslaontarget.health.os._exit"):
            monitor.check_interval = 0.02
            monitor.start()
            first = monitor._thread
            monitor.start()  # already running -> same thread
            assert monitor._thread is first
            monitor.stop()

    def test_stop_without_start_is_safe(self, monitor):
        monitor.stop()  # no thread -> no raise
