"""Health monitoring for TeslaOnTarget.

Tracks last successful TAK sends and writes a health JSON file.
Can attempt reconnects and optionally exit for supervisor restarts
if no traffic has been sent for a configured period.
"""

from __future__ import annotations

import json
import os
import threading
import time
import logging
from typing import Optional

logger = logging.getLogger(__name__)


class HealthMonitor:
    """Background health monitor bound to a shared TAK client."""

    def __init__(
        self,
        tak_client,
        health_file: str = "health.json",
        max_no_send_seconds: int = 120,
        check_interval: int = 15,
        hard_restart_seconds: Optional[int] = None,
    ):
        self.tak_client = tak_client
        self.health_file = health_file
        self.max_no_send_seconds = max_no_send_seconds
        self.check_interval = check_interval
        self.hard_restart_seconds = hard_restart_seconds or (max_no_send_seconds * 5)
        self._stop = threading.Event()
        self._thread: Optional[threading.Thread] = None

    def start(self):
        if self._thread and self._thread.is_alive():
            return
        self._stop.clear()
        self._thread = threading.Thread(target=self._run, name="HealthMonitor", daemon=True)
        self._thread.start()
        logger.info(
            "Health monitor started (no-send threshold=%ss, check=%ss, hard-restart=%ss)",
            self.max_no_send_seconds,
            self.check_interval,
            self.hard_restart_seconds,
        )

    def stop(self):
        self._stop.set()
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=2)

    def _write_snapshot(self, snapshot: dict):
        try:
            tmp = self.health_file + ".tmp"
            with open(tmp, "w") as f:
                json.dump(snapshot, f, indent=2)
            os.replace(tmp, self.health_file)
        except Exception as e:
            logger.warning("Failed writing health file %s: %s", self.health_file, e)

    def _run(self):
        while not self._stop.is_set():
            now = time.time()
            snap = self.tak_client.health_snapshot() if hasattr(self.tak_client, "health_snapshot") else {}
            last_ok = snap.get("last_send_ok")

            # Compute staleness
            stale_for = None
            if last_ok is not None:
                stale_for = max(0, int(now - last_ok))
            else:
                # Never sent yet; consider stale from process start
                stale_for = None

            # Write health file
            snapshot = {
                "time": now,
                "connected": snap.get("connected"),
                "tak": snap,
                "stale_seconds": stale_for,
                "threshold_seconds": self.max_no_send_seconds,
            }
            self._write_snapshot(snapshot)

            # Act if stale
            if stale_for is not None and stale_for > self.max_no_send_seconds:
                logger.warning(
                    "No successful TAK send for %ss (> %ss). Forcing reconnect.",
                    stale_for,
                    self.max_no_send_seconds,
                )
                try:
                    self.tak_client.disconnect()
                except Exception:
                    pass
                self.tak_client.start_background_reconnect()

            # Escalate to hard restart if far beyond threshold
            if (
                stale_for is not None
                and self.hard_restart_seconds is not None
                and stale_for > self.hard_restart_seconds
            ):
                logger.error(
                    "Health critical: no TAK send for %ss (> %ss). Exiting for supervisor restart.",
                    stale_for,
                    self.hard_restart_seconds,
                )
                # Exit the process to allow systemd/docker to restart it
                os._exit(12)

            # Sleep with stop awareness
            self._stop.wait(self.check_interval)

