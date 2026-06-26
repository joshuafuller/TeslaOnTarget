"""Tests for teslaontarget.config_handler.Config (config loading + validation)."""
import importlib.util

import pytest

import teslaontarget.config_handler as ch
from teslaontarget.config_handler import Config

_DEFAULTS = {
    "COT_URL": Config.COT_URL,
    "API_LOOP_DELAY": Config.API_LOOP_DELAY,
    "DEAD_RECKONING_DELAY": Config.DEAD_RECKONING_DELAY,
    "TESLA_USERNAME": Config.TESLA_USERNAME,
    "LAST_POSITION_FILE": Config.LAST_POSITION_FILE,
    "MPH_TO_MS": Config.MPH_TO_MS,
}


@pytest.fixture(autouse=True)
def reset_config(monkeypatch):
    monkeypatch.delenv("TESLAONTARGET_CONFIG", raising=False)
    for k, v in _DEFAULTS.items():
        setattr(Config, k, v)
    yield
    for k, v in _DEFAULTS.items():
        setattr(Config, k, v)


def _write_config(tmp_path, body, name="config.py"):
    p = tmp_path / name
    p.write_text(body)
    return str(p)


class TestLoadFromFile:
    def test_explicit_path_loads_public_attrs(self, tmp_path):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "a@b.com"\nCOT_URL = "tcp://h:1"\n_PRIVATE = 9\n')
        Config.load_from_file(path)
        assert Config.TESLA_USERNAME == "a@b.com"
        assert Config.COT_URL == "tcp://h:1"
        assert not hasattr(Config, "_PRIVATE")  # underscore names are skipped

    def test_env_var_path_is_used(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "env@b.com"\n')
        monkeypatch.setenv("TESLAONTARGET_CONFIG", path)
        Config.load_from_file()
        assert Config.TESLA_USERNAME == "env@b.com"

    def test_env_var_tilde_is_expanded(self, tmp_path, monkeypatch):
        _write_config(tmp_path, 'TESLA_USERNAME = "tilde@b.com"\n')
        monkeypatch.setenv("HOME", str(tmp_path))
        monkeypatch.setenv("TESLAONTARGET_CONFIG", "~/config.py")
        Config.load_from_file()
        assert Config.TESLA_USERNAME == "tilde@b.com"

    def test_env_var_pointing_at_directory_falls_back(self, tmp_path, monkeypatch):
        # A directory is not a file -> env var ignored -> falls through to the
        # package-adjacent path (which doesn't exist in tests) -> defaults kept.
        monkeypatch.setenv("TESLAONTARGET_CONFIG", str(tmp_path))
        Config.load_from_file()
        assert Config.TESLA_USERNAME is None

    def test_missing_explicit_path_keeps_defaults(self, tmp_path):
        Config.load_from_file(str(tmp_path / "absent.py"))
        assert Config.TESLA_USERNAME is None

    def test_no_path_and_no_env_uses_package_fallback(self):
        # config_path None and TESLAONTARGET_CONFIG unset (fixture) -> falls
        # through to the package-adjacent config.py (absent in tests).
        Config.load_from_file()
        assert Config.TESLA_USERNAME is None

    def test_syntax_error_in_config_is_caught(self, tmp_path):
        path = _write_config(tmp_path, "this is not valid python =\n")
        Config.load_from_file(path)  # must not raise
        assert Config.TESLA_USERNAME is None

    def test_none_spec_is_guarded(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "x@y.com"\n')
        monkeypatch.setattr(importlib.util, "spec_from_file_location", lambda *a, **k: None)
        Config.load_from_file(path)  # guarded, must not raise
        assert Config.TESLA_USERNAME is None

    def test_none_loader_is_guarded(self, tmp_path, monkeypatch):
        path = _write_config(tmp_path, 'TESLA_USERNAME = "x@y.com"\n')

        class _SpecNoLoader:
            loader = None

        monkeypatch.setattr(importlib.util, "spec_from_file_location",
                            lambda *a, **k: _SpecNoLoader())
        Config.load_from_file(path)
        assert Config.TESLA_USERNAME is None


class TestValidate:
    def test_valid_when_username_and_cot_url_set(self):
        Config.TESLA_USERNAME = "a@b.com"
        Config.COT_URL = "tcp://h:1"
        assert Config.validate() is True

    def test_invalid_without_username(self):
        Config.TESLA_USERNAME = None
        Config.COT_URL = "tcp://h:1"
        assert Config.validate() is False

    def test_invalid_without_cot_url(self):
        Config.TESLA_USERNAME = "a@b.com"
        Config.COT_URL = ""
        assert Config.validate() is False
