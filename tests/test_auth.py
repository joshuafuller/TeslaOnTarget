"""Tests for teslaontarget.auth.main (interactive Tesla auth, fully mocked)."""
from unittest.mock import MagicMock, patch

import pytest

from teslaontarget import auth


@pytest.fixture
def tesla():
    with patch("teslaontarget.auth.Tesla") as T, patch("teslaontarget.auth.Config"):
        yield T.return_value


def test_already_authorized_tests_connection_and_returns(tesla, capsys):
    tesla.authorized = True
    tesla.vehicle_list.return_value = [{"display_name": "Tron", "state": "online"}]
    auth.main()
    out = capsys.readouterr().out
    assert "Already authenticated" in out
    tesla.fetch_token.assert_not_called()


def test_authorized_but_token_invalid_falls_through_to_reauth(tesla):
    tesla.authorized = True
    # first vehicle_list (validation) fails, second (after fetch_token) succeeds
    tesla.vehicle_list.side_effect = [Exception("invalid"),
                                      [{"display_name": "X", "vin": "123456789"}]]
    tesla.authorization_url.return_value = "https://auth"
    with patch("teslaontarget.auth.webbrowser.open"), \
         patch("builtins.input", return_value="https://redirect?code=abc"):
        auth.main()
    tesla.fetch_token.assert_called_once()


def test_fresh_auth_opens_browser_and_fetches_token(tesla):
    tesla.authorized = False
    tesla.authorization_url.return_value = "https://auth"
    tesla.vehicle_list.return_value = [{"display_name": "X", "vin": "7SAYGDEF4PF751099"}]
    with patch("teslaontarget.auth.webbrowser.open") as wb, \
         patch("builtins.input", return_value="https://r?code=abc"):
        auth.main()
    wb.assert_called_once_with("https://auth")
    tesla.fetch_token.assert_called_once_with(authorization_response="https://r?code=abc")


def test_browser_open_failure_prints_manual_url(tesla, capsys):
    tesla.authorized = False
    tesla.authorization_url.return_value = "https://auth"
    tesla.vehicle_list.return_value = []
    with patch("teslaontarget.auth.webbrowser.open", side_effect=Exception("no display")), \
         patch("builtins.input", return_value="https://r"):
        auth.main()
    assert "manually open" in capsys.readouterr().out
    tesla.fetch_token.assert_called_once()


def test_fetch_token_failure_is_handled(tesla, capsys):
    tesla.authorized = False
    tesla.authorization_url.return_value = "https://auth"
    tesla.fetch_token.side_effect = Exception("bad code")
    with patch("teslaontarget.auth.webbrowser.open"), \
         patch("builtins.input", return_value="https://r"):
        auth.main()  # must not raise
    assert "Authentication failed" in capsys.readouterr().out
