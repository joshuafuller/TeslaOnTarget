"""Shared test configuration.

Disable Hypothesis's per-example deadline: under coverage/mutation instrumentation
(pytest-cov, mutmut) the code under test runs slower and would otherwise trip the
default 200ms deadline, producing flaky failures unrelated to behavior.
"""
from hypothesis import HealthCheck, settings

settings.register_profile(
    "default",
    deadline=None,
    suppress_health_check=[HealthCheck.too_slow],
)
settings.load_profile("default")
