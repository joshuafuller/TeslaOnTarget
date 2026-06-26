"""Tests for teslaontarget.utils — pure helpers (math, unit conversion, JSON IO)."""
import json
import math

import pytest
from hypothesis import HealthCheck, given, settings, strategies as st


from teslaontarget.utils import (
    calculate_distance,
    load_json_file,
    save_json_file,
    meters_to_feet,
    mph_to_ms,
    celsius_to_fahrenheit,
)

# Robust under mutmut/coverage instrumentation (no deadline; allow class-method
# property tests to run under different executors across mutation runs).
_PROP = settings(deadline=None, suppress_health_check=[HealthCheck.differing_executors])

# ---- coordinates (lat in [-90,90], lon in [-180,180]) ----
_lats = st.floats(min_value=-89.9, max_value=89.9, allow_nan=False, allow_infinity=False)
_lons = st.floats(min_value=-179.9, max_value=179.9, allow_nan=False, allow_infinity=False)


class TestCalculateDistance:
    def test_zero_distance_for_identical_points(self):
        assert calculate_distance(30.0, -87.0, 30.0, -87.0) == pytest.approx(0.0, abs=1e-6)

    def test_known_distance_one_degree_latitude(self):
        # One degree of latitude is ~111.19 km along a meridian.
        d = calculate_distance(0.0, 0.0, 1.0, 0.0)
        assert d == pytest.approx(111195, rel=0.001)

    def test_equator_quarter_circumference(self):
        # 0E -> 90E on the equator is a quarter of Earth's circumference.
        d = calculate_distance(0.0, 0.0, 0.0, 90.0)
        assert d == pytest.approx(2 * math.pi * 6371e3 / 4, rel=0.001)

    @_PROP
    @given(_lats, _lons, _lats, _lons)
    def test_symmetry(self, a, b, c, d):
        assert calculate_distance(a, b, c, d) == pytest.approx(
            calculate_distance(c, d, a, b), rel=1e-9, abs=1e-6)

    @_PROP
    @given(_lats, _lons, _lats, _lons)
    def test_non_negative_and_bounded(self, a, b, c, d):
        dist = calculate_distance(a, b, c, d)
        assert dist >= 0
        # Can never exceed half the Earth's circumference (antipodal max).
        assert dist <= math.pi * 6371e3 + 1

    @_PROP
    @given(_lats, _lons)
    def test_identity_is_zero(self, lat, lon):
        assert calculate_distance(lat, lon, lat, lon) == pytest.approx(0.0, abs=1e-3)


class TestUnitConversions:
    def test_meters_to_feet_known(self):
        assert meters_to_feet(1.0) == pytest.approx(3.28084)
        assert meters_to_feet(0) == 0

    @_PROP
    @given(st.floats(min_value=0, max_value=1e6, allow_nan=False))
    def test_meters_to_feet_scale(self, m):
        assert meters_to_feet(m) == pytest.approx(m * 3.28084)

    def test_mph_to_ms_known(self):
        assert mph_to_ms(100) == pytest.approx(44.704)

    @pytest.mark.parametrize("falsy", [0, 0.0, None])
    def test_mph_to_ms_falsy_returns_zero(self, falsy):
        assert mph_to_ms(falsy) == 0

    @_PROP
    @given(st.floats(min_value=0.001, max_value=1000, allow_nan=False))
    def test_mph_to_ms_positive_is_scaled(self, mph):
        assert mph_to_ms(mph) == pytest.approx(mph * 0.44704)

    def test_celsius_to_fahrenheit_known(self):
        assert celsius_to_fahrenheit(0) == 32
        assert celsius_to_fahrenheit(100) == 212
        assert celsius_to_fahrenheit(-40) == -40

    def test_celsius_to_fahrenheit_none(self):
        assert celsius_to_fahrenheit(None) is None

    @_PROP
    @given(st.floats(min_value=-273, max_value=1000, allow_nan=False))
    def test_celsius_to_fahrenheit_formula(self, c):
        assert celsius_to_fahrenheit(c) == pytest.approx((c * 9 / 5) + 32)


class TestJsonIO:
    def test_save_then_load_roundtrip(self, tmp_path):
        p = tmp_path / "data.json"
        payload = {"a": 1, "b": [1, 2, 3], "c": "x"}
        assert save_json_file(str(p), payload) is True
        assert load_json_file(str(p)) == payload

    def test_load_missing_file_returns_none(self, tmp_path):
        assert load_json_file(str(tmp_path / "nope.json")) is None

    def test_load_malformed_json_returns_none(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{not valid json")
        assert load_json_file(str(p)) is None

    def test_save_to_unwritable_path_returns_false(self, tmp_path):
        # Parent directory does not exist -> open() raises -> caught -> False.
        bad = tmp_path / "missing_dir" / "data.json"
        assert save_json_file(str(bad), {"a": 1}) is False

    def test_save_writes_indented_json(self, tmp_path):
        p = tmp_path / "out.json"
        save_json_file(str(p), {"k": "v"})
        text = p.read_text()
        assert json.loads(text) == {"k": "v"}
        assert "\n" in text  # indent=2 produces multiline output
