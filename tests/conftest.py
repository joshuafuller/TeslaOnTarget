"""Shared test configuration.

Disable Hypothesis's per-example deadline: under coverage/mutation instrumentation
(pytest-cov, mutmut) the code under test runs slower and would otherwise trip the
default 200ms deadline, producing flaky failures unrelated to behavior.
"""
import pytest
from hypothesis import HealthCheck, settings

from teslaontarget.config_handler import AppConfig

settings.register_profile(
    "default",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("default")


@pytest.fixture
def make_config():
    """Factory for AppConfig with sane test defaults; override any field."""
    def _make(**overrides):
        defaults = dict(
            cot_url="tcp://h:1",
            tesla_username="t@e.com",
            api_loop_delay=10,
            dead_reckoning_delay=1,
            last_position_file="last.json",
        )
        defaults.update(overrides)
        return AppConfig(**defaults)
    return _make
