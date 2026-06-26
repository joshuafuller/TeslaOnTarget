"""Command line interface for TeslaOnTarget."""

import os
import sys
import time
import signal
import logging
import argparse
import threading

from teslapy import Tesla

from .tesla_api import TeslaCoT
from .tak_client import TAKClient
from .config_handler import load_config
from .health import HealthMonitor

logger = logging.getLogger(__name__)

# Global flag for graceful shutdown (flipped by the signal handler).
running = True


def _make_log_handlers():
    """Build logging handlers: always stdout, plus a file handler when writable."""
    handlers = [logging.StreamHandler()]
    try:
        if os.path.exists('/logs') and os.access('/logs', os.W_OK):
            log_path = '/logs/teslaontarget.log'
        else:
            log_path = 'teslaontarget.log'
        handlers.append(logging.FileHandler(log_path))
    except (IOError, OSError) as e:
        print(f"Warning: Unable to create log file: {e}. Logging to stdout only.")
    return handlers


def _configure_logging():
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=_make_log_handlers(),
    )


_configure_logging()


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received")
    running = False


def _parse_args():
    parser = argparse.ArgumentParser(description='Bridge Tesla vehicles with TAK servers')
    parser.add_argument('--config', help='Path to config.py file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    return parser.parse_args()


def _load_and_validate_config(args):
    """Apply --debug, load config, and exit(1) if it does not validate."""
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    config = load_config(args.config)
    if not config.validate():
        logger.error("Invalid configuration. Please check config.py")
        sys.exit(1)
    return config


def _select_vehicles(tesla, config):
    """Return vehicles to track, applying the configured filter. Exits if none."""
    vehicles = tesla.vehicle_list()
    if not vehicles:
        logger.error("No vehicles found on Tesla account")
        sys.exit(1)
    logger.info(f"Found {len(vehicles)} vehicle(s) on account")

    vehicle_filter = config.vehicle_filter
    if not vehicle_filter:
        logger.info("No vehicle filter configured - tracking all vehicles")
        return vehicles

    filtered = []
    for vehicle in vehicles:
        display_name = vehicle.get('display_name', '')
        vin = vehicle.get('vin', '')
        if display_name in vehicle_filter or vin in vehicle_filter:
            filtered.append(vehicle)
            logger.info(f"Selected vehicle: {display_name} (VIN: {vin})")
    if not filtered:
        logger.error(f"No vehicles matched the filter: {vehicle_filter}")
        sys.exit(1)
    logger.info(f"Tracking {len(filtered)} vehicle(s) based on filter")
    return filtered


def _build_health_monitor(tak_client, config):
    """Construct a HealthMonitor from config, treating <=0 thresholds as unset."""
    configured_no_send = config.health_no_send_seconds or 0
    configured_check = config.health_check_interval or 0
    configured_hard = config.health_hard_restart_seconds or 0
    health_file = config.health_file

    default_no_send = max(120, config.api_loop_delay * 8)
    max_no_send = configured_no_send if configured_no_send > 0 else default_no_send
    check_interval = configured_check if configured_check > 0 else 15
    hard_restart = configured_hard if configured_hard > 0 else (max_no_send * 5)

    logger.info(
        "Health thresholds: no-send=%ss, check=%ss, hard-restart=%ss -> file=%s",
        max_no_send, check_interval, hard_restart, health_file,
    )
    return HealthMonitor(
        tak_client, health_file=health_file, max_no_send_seconds=max_no_send,
        check_interval=check_interval, hard_restart_seconds=hard_restart,
        alert_url=config.alert_webhook_url,
    )


def _wake_vehicles(vehicles):
    """Send a wake command to any asleep vehicle (best-effort)."""
    logger.info("Waking up vehicles...")
    for vehicle in vehicles:
        try:
            if vehicle.get("state") == "asleep":
                logger.info(f"Waking up {vehicle['display_name']}...")
                vehicle.sync_wake_up()
        except Exception as e:
            logger.warning(f"Could not wake {vehicle['display_name']}: {e}")


def _start_tracking_threads(vehicles, tak_client, config):
    """Spawn one daemon tracking thread per vehicle; return the thread list."""
    threads = []
    for vehicle in vehicles:
        vehicle_id = vehicle.get('vin', vehicle.get('id_s', 'unknown'))
        tesla_cot = TeslaCoT(config, vehicle_id=vehicle_id, tak_client=tak_client)
        logger.info(f"Starting tracking for {vehicle['display_name']} (VIN: {vehicle.get('vin', 'N/A')})")
        thread = threading.Thread(
            target=tesla_cot.fetch_and_send_data_for_vehicle,
            args=(vehicle,), daemon=True,
            name=f"Vehicle-{vehicle['display_name']}",
        )
        thread.start()
        threads.append(thread)
    return threads


def _monitor_threads(threads, config):
    """Watch tracking threads until shutdown is requested."""
    logger.info("All tracking threads started")
    logger.info(f"Sending updates every {config.api_loop_delay} seconds")
    logger.info("Press Ctrl+C to stop\n")
    while running:
        alive_count = sum(1 for t in threads if t.is_alive())
        if alive_count < len(threads):
            logger.warning(f"Only {alive_count}/{len(threads)} threads running")
        time.sleep(5)


def _stop_health(health):
    """Stop the health monitor if one was started (best-effort)."""
    if health is None:
        return
    try:
        health.stop()
    except Exception:
        pass


def main():
    """Main entry point for TeslaOnTarget."""
    args = _parse_args()
    config = _load_and_validate_config(args)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    logger.info("Starting TeslaOnTarget...")

    health = None
    try:
        tesla = Tesla(config.tesla_username)
        vehicles = _select_vehicles(tesla, config)

        shared_tak_client = TAKClient(config.cot_url)

        health = _build_health_monitor(shared_tak_client, config)
        health.start()

        _wake_vehicles(vehicles)
        threads = _start_tracking_threads(vehicles, shared_tak_client, config)
        _monitor_threads(threads, config)
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("TeslaOnTarget stopped")
        _stop_health(health)


if __name__ == '__main__':
    main()
