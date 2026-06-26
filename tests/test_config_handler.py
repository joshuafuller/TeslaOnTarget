"""Tests for teslaontarget.config_handler (AppConfig + load_config)."""
import dataclasses
import importlib.util

import pytest

from teslaontarget.config_handler import AppConfig, load_config


def _write_config(tmp_path, body, name="config.py"):
    p = tmp_path / name
    p.write_text(body)
    return str(p)


@pytest.fixture(autouse=True)
def _no_env(monkeypatch):
    monkeypatch.delenv("TESLAONTARGET_CONFIG", raising=False)


class TestAppConfig:
    def test_defaults(self):
        c = AppConfig()
        assert c.tesla_username is None
        assert c.api_loop_delay == 10
        assert c.debug_mode is False
        assert c.vehicle_filter == ()

    def test_is_immutable(self):
        with pytest.raises(dataclasses.FrozenInstanceError):
            AppConfig().api_loop_delay = 5

    def test_validate_ok(self):
        assert AppConfig(tesla_username="a@b.com", cot_url="tcp://h:1").validate() is True

    def test_validate_missing_username(self):
        assert AppConfig(tesla_username=None, cot_url="tcp://h:1").validate() is False

    def test_validate_missing_cot_url(self):
        assert AppConfig(tesla_username="a@b.com", cot_url="").validate() is False


class TestLoadConfig:
    def test_explicit_path_maps_upper_to_fields(self, tmp_path):
        path = _write_config(
            tmp_path,
            'COT_URL = "tcp://x:1"\nTESLA_USERNAME = "a@b.com"\nAPI_LOOP_DELAY = 30\n'
            'DEBUG_MODE = True\n')
        c = load_config(path)
        assert c.cot_url == "tcp://x:1"
        assert c.tesla_username == "a@b.com"
        assert c.api_loop_delay == 30
        assert c.debug_mode is True

    def test_unknown_keys_ignored(self, tmp_path):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "a@b.com"\nSOMETHING_ELSE = 9\n_PRIV = 1\n')
        c = load_config(path)
        assert c.tesla_username == "a@b.com"
        assert not hasattr(c, "something_else")

    def test_vehicle_filter_list_becomes_tuple(self, tmp_path):
        path = _write_config(tmp_path, 'VEHICLE_FILTER = ["Tron", "Other"]\n')
        assert load_config(path).vehicle_filter == ("Tron", "Other")

    def test_env_var_path(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "env@b.com"\n')
        monkeypatch.setenv("TESLAONTARGET_CONFIG", path)
        assert load_config().tesla_username == "env@b.com"

    def test_env_var_tilde_expanded(self, tmp_path, monkeypatch):
        _write_config(tmp_path, 'TESLA_USERNAME = "tilde@b.com"\n')
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("TESLAONTARGET_CONFIG", "~/config.py")
        assert load_config().tesla_username == "tilde@b.com"

    def test_env_var_directory_falls_back_to_defaults(self, tmp_path, monkeypatch):
        monkeypatch.setenv("TESLAONTARGET_CONFIG", str(tmp_path))
        assert load_config().tesla_username is None

    def test_missing_file_returns_defaults(self, tmp_path):
        assert load_config(str(tmp_path / "absent.py")).tesla_username is None

    def test_no_path_no_env_uses_package_fallback(self):
        assert load_config().tesla_username is None  # package-adjacent config absent in tests

    def test_syntax_error_returns_defaults(self, tmp_path):
        path = _write_config(tmp_path, "this is not valid python =\n")
        assert load_config(path).tesla_username is None

    def test_none_spec_returns_defaults(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "x@y.com"\n')
        monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
        assert load_config(path).tesla_username is None

    def test_none_loader_returns_defaults(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "x@y.com"\n')

        class _SpecNoLoader:
            loader = None

        monkeypatch.setattr(importlib.util, "spec_from_file_location",
                            lambda *a, **k: _SpecNoLoader())
        assert load_config(path).tesla_username is None
