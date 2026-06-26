#!/usr/bin/env python3
"""Deterministic mutation-testing harness for TeslaOnTarget.

Why this exists instead of mutmut: mutmut 3.x does not route test imports to its
mutated `mutants/` copy in this uv/installed-package setup, so it reports every
mutant as "survived" even though the suite demonstrably kills mutations. This
harness applies a curated set of *meaningful* source mutations to the real
package, runs the test suite, and asserts each mutation is caught (a failing
test == a killed mutant). A surviving mutant means the test net is too weak for
that behavior and must be strengthened.

Usage:  uv run python scripts/mutation_check.py
Exit 0 if all mutants are killed; exit 1 (and lists survivors) otherwise.
"""
from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

# Never write .pyc while mutating: the mutate->import->revert cycle can finish
# within one mtime tick, leaving a stale *mutated* .pyc that later imports reuse.
_ENV = {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"}

ROOT = Path(__file__).resolve().parent.parent

# (module, original_snippet, mutated_snippet, test_target, description)
MUTATIONS = [
    # ---- utils.py ----
    ("teslaontarget/utils.py", "return R * c", "return R + c",
     "tests/test_utils.py", "distance: R*c -> R+c"),
    ("teslaontarget/utils.py", "c = 2 * atan2", "c = 1 * atan2",
     "tests/test_utils.py", "distance: 2*atan2 -> 1*atan2"),
    ("teslaontarget/utils.py", "return mph * MPH_TO_MS if mph else 0",
     "return mph * MPH_TO_MS if not mph else 0",
     "tests/test_utils.py", "mph_to_ms: guard negation"),
    ("teslaontarget/utils.py", "return mph * MPH_TO_MS if mph else 0",
     "return mph / MPH_TO_MS if mph else 0",
     "tests/test_utils.py", "mph_to_ms: * -> / MPH_TO_MS"),
    ("teslaontarget/utils.py", "return (celsius * 9/5) + 32 if celsius is not None else None",
     "return (celsius * 9/5) - 32 if celsius is not None else None",
     "tests/test_utils.py", "c_to_f: +32 -> -32"),
    ("teslaontarget/utils.py", "return meters * METERS_TO_FEET", "return meters / METERS_TO_FEET",
     "tests/test_utils.py", "meters_to_feet: * -> / METERS_TO_FEET"),

    # ---- cot.py ----
    ("teslaontarget/cot.py", "if speed and speed > 1:", "if speed and speed > 1000:",
     "tests/test_cot.py", "cot: moving-speed threshold 1 -> 1000"),
    ("teslaontarget/cot.py", 'ce = "5.0"  # Better accuracy', 'ce = "12.5"  # Better accuracy',
     "tests/test_cot.py", "cot: moving CE 5.0 -> 12.5"),
    ("teslaontarget/cot.py", "speed_ms = speed_mph * MPH_TO_MS", "speed_ms = speed_mph / MPH_TO_MS",
     "tests/test_cot.py", "cot: track speed conversion * -> /"),
    ("teslaontarget/cot.py", "stale = now + timedelta(minutes=5)", "stale = now + timedelta(minutes=4)",
     "tests/test_cot.py", "cot: stale window 5 -> 4 min"),
    ("teslaontarget/cot.py", 'if charge_state in ["Disconnected", "Complete", None]:',
     'if charge_state not in ["Disconnected", "Complete", None]:',
     "tests/test_cot.py", "cot: charging guard inverted"),
    ("teslaontarget/cot.py", "if not (shift_state == \"P\" or shift_state is None):",
     "if (shift_state == \"P\" or shift_state is None):",
     "tests/test_cot.py", "cot: security guard inverted"),

    # ---- config_handler.py ----
    ("teslaontarget/config_handler.py", "if not cls.TESLA_USERNAME:",
     "if cls.TESLA_USERNAME:",
     "tests/test_config_handler.py", "config: username validation inverted"),
    ("teslaontarget/config_handler.py", "if os.path.isfile(env_path):",
     "if not os.path.isfile(env_path):",
     "tests/test_config_handler.py", "config: env isfile inverted"),

    # ---- tak_client.py ----
    ("teslaontarget/tak_client.py", "self.connected = True\n            self.last_connect_ok",
     "self.connected = False\n            self.last_connect_ok",
     "tests/test_tak_client.py", "tak: connect leaves connected False"),
    ("teslaontarget/tak_client.py", "self.last_send_ok = time.time()\n                return True",
     "self.last_send_ok = time.time()\n                return False",
     "tests/test_tak_client.py", "tak: send_cot returns False on success"),

    # ---- health.py ----
    ("teslaontarget/health.py", "return max(0, int(now - last_ok))",
     "return max(0, int(now + last_ok))",
     "tests/test_health.py", "health: staleness now-last -> now+last"),
    ("teslaontarget/health.py", "if stale_for is not None and stale_for > self.max_no_send_seconds:",
     "if stale_for is not None and stale_for < self.max_no_send_seconds:",
     "tests/test_health.py", "health: stale comparison flipped"),
    ("teslaontarget/health.py", "self.hard_restart_seconds = hard_restart_seconds or (max_no_send_seconds * 5)",
     "self.hard_restart_seconds = hard_restart_seconds or (max_no_send_seconds * 4)",
     "tests/test_health.py", "health: hard-restart default *5 -> *4"),

    # ---- tesla_api.py ----
    ("teslaontarget/tesla_api.py", "self.rate_limit_backoff = min(self.rate_limit_backoff * 2, 32)",
     "self.rate_limit_backoff = min(self.rate_limit_backoff * 1, 32)",
     "tests/test_tesla_api.py", "tesla: rate-limit backoff *2 -> *1"),
    ("teslaontarget/tesla_api.py", "if self.consecutive_errors >= 3:",
     "if self.consecutive_errors > 3:",
     "tests/test_tesla_api.py", "tesla: error escalation >=3 -> >3"),
    ('teslaontarget/tesla_api.py', 'if "vehicle unavailable" in error_str or "asleep" in error_str:',
     'if "vehicle unavailable" in error_str and "asleep" in error_str:',
     "tests/test_tesla_api.py", "tesla: unavailable classify or -> and"),
    # ---- vehicle_mapper.py ----
    ("teslaontarget/vehicle_mapper.py",
     'return f"TESLA-{hashlib.md5(str(vehicle_id).encode(), usedforsecurity=False).hexdigest()[:8]}"',
     'return f"TESLA-{hashlib.md5(str(vehicle_id).encode(), usedforsecurity=False).hexdigest()[:7]}"',
     "tests/test_vehicle_mapper.py", "mapper: UID md5 slice [:8] -> [:7]"),
    ("teslaontarget/vehicle_mapper.py", 'variant = "Performance"', 'variant = "Sport"',
     "tests/test_vehicle_mapper.py", "mapper: Performance variant label"),
    ("teslaontarget/tesla_api.py",
     "return data.get('latitude') is not None and data.get('longitude') is not None",
     "return data.get('latitude') is None and data.get('longitude') is not None",
     "tests/test_tesla_api.py", "tesla: _has_coordinates is-not-None -> is-None"),
]


def run() -> int:
    survivors = []
    for module, old, new, test, desc in MUTATIONS:
        path = ROOT / module
        original = path.read_text()
        if old not in original:
            print(f"  [ERROR ] anchor missing, cannot mutate: {desc}")
            survivors.append(desc + " (anchor missing)")
            continue
        path.write_text(original.replace(old, new, 1))
        try:
            result = subprocess.run(
                ["uv", "run", "pytest", test, "-q", "--no-header",
                 "-p", "no:cacheprovider"],
                cwd=ROOT, capture_output=True, text=True, timeout=180, env=_ENV,
            )
            killed = result.returncode != 0
        finally:
            path.write_text(original)  # always restore
        print(f"  [{'KILLED' if killed else 'SURVIVED'}] {desc}")
        if not killed:
            survivors.append(desc)

    total = len(MUTATIONS)
    print(f"\nMutation result: {total - len(survivors)}/{total} killed")
    if survivors:
        print("SURVIVORS (strengthen these tests):")
        for s in survivors:
            print(f"  - {s}")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(run())
