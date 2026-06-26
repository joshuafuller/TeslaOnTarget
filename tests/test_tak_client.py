"""Tests for teslaontarget.tak_client.TAKClient (socket boundary, mocked)."""
import socket
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget.tak_client import TAKClient


@pytest.fixture
def client():
    return TAKClient("tcp://10.0.0.5:8087")


class TestInit:
    def test_parses_host_and_port(self, client):
        assert client.host == "10.0.0.5"
        assert client.port == 8087

    def test_initial_state(self, client):
        assert client.socket is None
        assert client.connected is False
        assert client.last_send_ok is None
        assert client.last_error is None


class TestConnect:
    def test_connect_success(self, client):
        with patch("teslaontarget.tak_client.socket.socket") as sock_cls:
            sock = sock_cls.return_value
            assert client.connect() is True
            assert client.connected is True
            assert client.last_connect_ok is not None
            sock.settimeout.assert_called_once_with(10)
            sock.connect.assert_called_once_with(("10.0.0.5", 8087))
            sock.setsockopt.assert_called_once()

    def test_connect_disconnects_existing_socket_first(self, client):
        client.socket = MagicMock()
        with patch("teslaontarget.tak_client.socket.socket"):
            with patch.object(client, "disconnect", wraps=client.disconnect) as disc:
                client.connect()
                disc.assert_called_once()

    def test_connect_failure_returns_false(self, client):
        with patch("teslaontarget.tak_client.socket.socket") as sock_cls:
            sock_cls.return_value.connect.side_effect = socket.error("refused")
            assert client.connect() is False
            assert client.connected is False


class TestDisconnect:
    def test_closes_socket(self, client):
        sock = MagicMock()
        client.socket = sock
        client.connected = True
        client.disconnect()
        sock.close.assert_called_once()
        assert client.socket is None
        assert client.connected is False

    def test_close_error_is_swallowed(self, client):
        sock = MagicMock()
        sock.close.side_effect = OSError("bad")
        client.socket = sock
        client.disconnect()  # must not raise
        assert client.socket is None

    def test_joins_live_reconnect_thread(self, client):
        thread = MagicMock()
        thread.is_alive.return_value = True
        client.reconnect_thread = thread
        client.disconnect()
        thread.join.assert_called_once_with(timeout=2)


class TestSendCot:
    def test_send_when_connected(self, client):
        client.connected = True
        client.socket = MagicMock()
        assert client.send_cot(b"<event/>") is True
        client.socket.sendall.assert_called_once_with(b"<event/>")
        assert client.last_send_ok is not None
        assert client.last_send_attempt is not None

    def test_connects_first_when_disconnected(self, client):
        client.connected = False
        with patch.object(client, "connect", side_effect=lambda: setattr(client, "connected", True) or True) as conn:
            client.socket = MagicMock()
            assert client.send_cot(b"x") is True
            conn.assert_called_once()

    @patch("teslaontarget.tak_client.time.sleep")
    def test_retries_connect_until_success(self, sleep, client):
        client.connected = False
        calls = {"n": 0}

        def fake_connect():
            calls["n"] += 1
            if calls["n"] >= 2:
                client.connected = True
                client.socket = MagicMock()
                return True
            return False

        with patch.object(client, "connect", side_effect=fake_connect):
            assert client.send_cot(b"x") is True
        sleep.assert_called_with(30)  # waited after the first failed connect

    @patch("teslaontarget.tak_client.time.sleep")
    def test_send_error_then_reconnect_and_succeed(self, sleep, client):
        client.connected = True
        sock = MagicMock()
        sock.sendall.side_effect = [socket.error("broken pipe"), None]
        client.socket = sock

        def reconnect():
            client.connected = True
            return True

        with patch.object(client, "connect", side_effect=reconnect):
            assert client.send_cot(b"x") is True
        assert client.last_error == "broken pipe"
        assert client.last_error_time is not None


class TestEnsureConnected:
    def test_connects_when_not_connected(self, client):
        with patch.object(client, "connect", return_value=True) as conn:
            assert client.ensure_connected() is True
            conn.assert_called_once()

    def test_healthy_peek_returns_true(self, client):
        client.connected = True
        client.socket = MagicMock()
        client.socket.recv.return_value = b"x"
        assert client.ensure_connected() is True
        client.socket.setblocking.assert_any_call(0)
        client.socket.setblocking.assert_any_call(1)

    def test_closed_connection_reconnects(self, client):
        client.connected = True
        client.socket = MagicMock()
        client.socket.recv.return_value = b""  # peer closed
        with patch.object(client, "connect", return_value=True) as conn:
            assert client.ensure_connected() is True
            conn.assert_called_once()

    def test_socket_error_on_peek_is_ignored(self, client):
        client.connected = True
        client.socket = MagicMock()
        client.socket.recv.side_effect = socket.error("EAGAIN")
        assert client.ensure_connected() is True


class TestBackgroundReconnect:
    def test_start_spawns_thread_when_disconnected(self, client):
        client.connected = False
        client.reconnect_thread = None
        with patch("teslaontarget.tak_client.threading.Thread") as Thread:
            client.start_background_reconnect()
            Thread.assert_called_once()
            Thread.return_value.start.assert_called_once()

    def test_start_noop_when_connected(self, client):
        client.connected = True
        with patch("teslaontarget.tak_client.threading.Thread") as Thread:
            client.start_background_reconnect()
            Thread.assert_not_called()

    def test_background_reconnect_succeeds_and_exits(self, client):
        client.connected = False
        client.stop_reconnect = MagicMock()
        client.stop_reconnect.is_set.return_value = False
        with patch.object(client, "connect", return_value=True):
            client._background_reconnect()  # connects on first try, returns

    def test_background_reconnect_waits_then_stops(self, client):
        client.connected = False
        client.stop_reconnect = MagicMock()
        client.stop_reconnect.is_set.side_effect = [False, True]
        with patch.object(client, "connect", return_value=False):
            client._background_reconnect()
            client.stop_reconnect.wait.assert_called_once_with(client.reconnect_interval)

    def test_background_reconnect_skips_connect_when_already_connected(self, client):
        # Loop body runs once with connected=True -> skips connect, just waits.
        client.connected = True
        client.stop_reconnect = MagicMock()
        client.stop_reconnect.is_set.side_effect = [False, True]
        with patch.object(client, "connect") as conn:
            client._background_reconnect()
            conn.assert_not_called()
            client.stop_reconnect.wait.assert_called_once_with(client.reconnect_interval)


class TestHealthSnapshot:
    def test_snapshot_fields(self, client):
        client.connected = True
        client.last_send_ok = 123.0
        snap = client.health_snapshot()
        assert snap["host"] == "10.0.0.5"
        assert snap["port"] == 8087
        assert snap["connected"] is True
        assert snap["last_send_ok"] == 123.0
