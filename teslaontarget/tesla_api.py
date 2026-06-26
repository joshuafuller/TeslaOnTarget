import json
import logging
import os
import threading
import time
from collections import deque
from datetime import datetime
from math import cos, degrees, radians, sin

from .constants import EARTH_RADIUS_M, MPH_TO_MS
from .cot import format_cot_for_tak, generate_cot_packet
from .tak_client import TAKClient
from .vehicle_mapper import map_vehicle_data
from .utils import load_json_file, save_json_file

logger = logging.getLogger(__name__)

# Tesla get_vehicle_data endpoint sets
_INIT_ENDPOINTS = ('location_data;drive_state;charge_state;vehicle_state;'
                   'climate_state;vehicle_config;gui_settings')
_LOOP_ENDPOINTS = ('location_data;drive_state;charge_state;vehicle_state;'
                   'climate_state;vehicle_config')
# Substrings in an API error that mean "slow down" rather than "broken"
_RATE_LIMIT_MARKERS = ('429', 'rate limit', 'too many requests', 'timeout')


class TeslaCoT:
    def __init__(self, config, vehicle_id=None, tak_client=None):
        self.config = config

        # Vehicle-specific attributes
        self.vehicle_id = vehicle_id
        self.position_file = self._get_position_filename()
        self.last_known_valid_data = self.read_last_position_from_file()
        self.positions_queue = deque(maxlen=2)
        self.vehicle_uids = {}
        self.dead_reckoning_thread = None
        self.stop_dead_reckoning = threading.Event()

        # Use shared TAK client if provided, otherwise create new one
        self.tak_client = tak_client if tak_client else TAKClient(config.cot_url)
        self.tesla = None
        self.vehicle = None

        # Rate limiting tracking
        self.rate_limit_backoff = 1  # Multiplier for delays
        self.consecutive_errors = 0
        self.max_wake_attempts = 3
        # Loop state (promoted from a local so the loop body is testable)
        self.consecutive_no_gps_count = 0

        # Debug mode - captures all Tesla API responses (opt-in; off by default).
        self.debug_mode = config.debug_mode
        self.debug_dir = "tesla_api_captures"
        self.capture_count = 0
        if self.debug_mode:
            os.makedirs(self.debug_dir, exist_ok=True)
            if vehicle_id:
                logger.info(f"DEBUG MODE ENABLED for vehicle {vehicle_id}! API responses will be captured to {self.debug_dir}/")
        
    def _get_position_filename(self):
        """Generate vehicle-specific position filename."""
        if self.vehicle_id:
            # Create safe filename from vehicle ID
            safe_id = "".join(c for c in str(self.vehicle_id) if c.isalnum() or c in '-_')
            return f"last_position_{safe_id}.json"
        return self.config.last_position_file
    
    def read_last_position_from_file(self):
        """Read the last known position from file."""
        return load_json_file(self.position_file)
    
    def save_last_position_to_file(self, data):
        """Save the current position to file."""
        try:
            save_json_file(self.position_file, data)
        except Exception as e:
            logger.error(f"Error saving position: {e}")
    
    def save_debug_capture(self, vehicle_data, prefix="vehicle_data"):
        """Save full Tesla API response for debugging and replay."""
        if not self.debug_mode:
            return
            
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S_%f")
            filename = f"{prefix}_{timestamp}.json"
            filepath = os.path.join(self.debug_dir, filename)
            
            # Save the COMPLETE raw API response with metadata
            debug_data = {
                "capture_metadata": {
                    "timestamp": time.time(),
                    "datetime": datetime.now().isoformat(),
                    "prefix": prefix,
                    "version": "1.0"
                },
                "raw_api_response": vehicle_data  # This is the FULL unmodified Tesla API response
            }
            
            with open(filepath, 'w') as f:
                json.dump(debug_data, f, indent=2)
            
            self.capture_count += 1
            logger.info(f"Capture #{self.capture_count}: Saved FULL Tesla API response to {filepath}")
        except Exception as e:
            logger.error(f"Failed to save debug capture: {e}")
    
    def send_to_cot(self, data):
        """Send data to TAK server via CoT."""
        try:
            cot_packet = generate_cot_packet(data)
            cot_bytes = format_cot_for_tak(cot_packet)
            
            logger.info(f"Sending CoT for {data.get('display_name')} at {data.get('latitude')}, {data.get('longitude')}")
            
            if self.tak_client.send_cot(cot_bytes):
                logger.info(f"Successfully sent CoT packet for {data.get('vehicle_name', 'Unknown')} ({len(cot_bytes)} bytes)")
            else:
                logger.warning("Failed to send CoT packet - background reconnection may be in progress")
        except Exception as e:
            logger.error(f"Error sending CoT packet: {e}", exc_info=True)
    
    def dead_reckoning_update(self, initial_data):
        """Perform dead reckoning interpolation between Tesla API updates."""
        start_time = time.time()
        max_duration = self.config.api_loop_delay - 1  # Run for slightly less than API interval
        
        # Keep track of current position
        current_lat = initial_data.get('latitude')
        current_lon = initial_data.get('longitude')
        
        logger.info(f"Dead reckoning started for up to {max_duration}s from lat={current_lat}, lon={current_lon}")

        update_count = 0
        while not self.stop_dead_reckoning.is_set():
            # 0.0 is a valid coordinate (equator / prime meridian) -- check presence.
            if current_lat is not None and current_lon is not None:
                # Wait for the next update interval
                time.sleep(self.config.dead_reckoning_delay)
                
                # Calculate new position based on speed and heading
                speed = initial_data.get('speed', 0)
                if speed is None:
                    speed = 0
                
                # If speed is 0, just send the same position to maintain 1Hz updates
                if speed == 0:
                    # Still send position updates at 1Hz even when stopped
                    updated_data = initial_data.copy()
                    updated_data['latitude'] = current_lat
                    updated_data['longitude'] = current_lon
                    updated_data['timestamp'] = time.time()
                    updated_data['dead_reckoned'] = True
                    
                    update_count += 1
                    self.send_to_cot(updated_data)
                    
                    # Check if we should stop
                    if time.time() - start_time >= max_duration:
                        logger.info(f"Dead reckoning stopping after {update_count} updates - API update imminent")
                        break
                    continue
                    
                # Tesla API returns speed in mph
                speed_ms = speed * MPH_TO_MS
                heading = initial_data.get('heading', 0)
                if heading is None:
                    heading = 0
                heading_rad = radians(heading)
                
                # Calculate distance traveled in one update cycle
                distance = speed_ms * self.config.dead_reckoning_delay
                
                # Calculate new position from current position
                lat_rad = radians(current_lat)
                lon_rad = radians(current_lon)

                # Calculate new latitude/longitude (equirectangular step)
                new_lat_rad = lat_rad + (distance / EARTH_RADIUS_M) * cos(heading_rad)
                new_lon_rad = lon_rad + (distance / (EARTH_RADIUS_M * cos(lat_rad))) * sin(heading_rad)

                # Convert back to degrees
                current_lat = degrees(new_lat_rad)
                current_lon = degrees(new_lon_rad)
                
                # Create updated data packet
                updated_data = initial_data.copy()
                updated_data['latitude'] = current_lat
                updated_data['longitude'] = current_lon
                updated_data['timestamp'] = time.time()
                updated_data['dead_reckoned'] = True
                
                # Send updated position
                update_count += 1
                logger.debug(f"Dead reckoning update #{update_count}: lat={current_lat:.6f}, lon={current_lon:.6f}, distance={distance:.1f}m")
                self.send_to_cot(updated_data)
                
                # Check if we should stop (near next API update)
                if time.time() - start_time >= max_duration:
                    logger.info(f"Dead reckoning stopping after {update_count} updates - API update imminent")
                    break
            else:
                logger.warning("No valid position for dead reckoning")
                break

    def _wake_if_asleep(self, vehicle):
        """Send a wake command if the vehicle reports asleep (best-effort)."""
        if vehicle.get("state") == "asleep":
            logger.info("Vehicle is asleep. Attempting to wake for initial position...")
            try:
                vehicle.sync_wake_up()
                logger.info("Vehicle wake command sent, waiting for it to come online...")
                time.sleep(5)
            except Exception as e:
                logger.warning(f"Failed to wake vehicle: {e}")

    def _fetch_initial_data(self, vehicle):
        """Retry get_vehicle_data up to max_wake_attempts; return data or None."""
        attempts = 0
        while attempts < self.max_wake_attempts:
            try:
                vehicle_data = vehicle.get_vehicle_data(endpoints=_INIT_ENDPOINTS)
                logger.info("Successfully got initial vehicle data")
                self.save_debug_capture(vehicle_data, "initial_vehicle_data")
                return vehicle_data
            except Exception as e:
                attempts += 1
                logger.warning(f"Failed to get vehicle data (attempt {attempts}/{self.max_wake_attempts}): {e}")
                if attempts < self.max_wake_attempts:
                    time.sleep(10)
        return None

    def _seed_initial_position(self, vehicle):
        """Acquire the first fix and seed last-known position.

        Returns True if tracking should proceed, False if there is nothing to
        work with (no fresh data and no cached position).
        """
        logger.info(f"Initializing tracking for {vehicle.get('display_name', 'Unknown')}...")
        self._wake_if_asleep(vehicle)
        vehicle_data = self._fetch_initial_data(vehicle)
        if vehicle_data is None:
            logger.error(f"Failed to get initial vehicle data after {self.max_wake_attempts} attempts")
            if self.last_known_valid_data:
                logger.info("Using cached position data")
                self.send_to_cot(self.last_known_valid_data)
                return True
            logger.error(f"No cached data available for {vehicle.get('display_name', 'Unknown')}")
            return False
        initial_data = map_vehicle_data(vehicle_data, vehicle)
        if self._has_coordinates(initial_data):
            self.last_known_valid_data = initial_data
            self.save_last_position_to_file(initial_data)
            logger.info(f"Saved initial position: {initial_data.get('latitude')}, {initial_data.get('longitude')}")
        return True

    def _classify_api_error(self, error_str):
        """Classify a (lowercased) API error string: rate_limit / unavailable / other."""
        if any(marker in error_str for marker in _RATE_LIMIT_MARKERS):
            return "rate_limit"
        if "vehicle unavailable" in error_str or "asleep" in error_str:
            return "unavailable"
        return "other"

    def _handle_api_error(self, exc):
        """React to a get_vehicle_data failure; return seconds to sleep before retry."""
        kind = self._classify_api_error(str(exc).lower())
        if kind == "rate_limit":
            self.consecutive_errors += 1
            self.rate_limit_backoff = min(self.rate_limit_backoff * 2, 32)
            delay = self.config.api_loop_delay * self.rate_limit_backoff
            logger.warning(f"Rate limit detected! Backing off to {delay}s delay (error #{self.consecutive_errors})")
            logger.warning(f"Error details: {exc}")
            if self.last_known_valid_data:
                self.send_to_cot(self.last_known_valid_data)
            return delay
        if kind == "unavailable":
            logger.info("Vehicle is asleep/unavailable. Using last known position.")
            if self.last_known_valid_data:
                self.send_to_cot(self.last_known_valid_data)
            else:
                logger.warning("No last known position available")
            return self.config.api_loop_delay
        # other
        self.consecutive_errors += 1
        logger.error(f"API error (#{self.consecutive_errors}): {exc}")
        if self.consecutive_errors >= 3:
            self.rate_limit_backoff = min(self.rate_limit_backoff * 1.5, 16)
            delay = self.config.api_loop_delay * self.rate_limit_backoff
            logger.warning(f"Multiple API errors detected. Backing off to {delay}s delay")
            return delay
        return self.config.api_loop_delay

    def _start_dead_reckoning(self, data):
        """(Re)start the dead-reckoning thread for the given position, if moving."""
        if self.dead_reckoning_thread and self.dead_reckoning_thread.is_alive():
            logger.debug("Restarting dead reckoning with new position")
            self.stop_dead_reckoning.set()
            self.dead_reckoning_thread.join(timeout=1)
        speed = data.get('speed', 0)
        shift_state = data.get('shift_state')
        if (speed is not None and speed > 0) or shift_state in ['D', 'R']:
            logger.info(f"Starting dead reckoning interpolation (speed: {speed}mph, gear: {shift_state})")
            self.stop_dead_reckoning.clear()
            self.dead_reckoning_thread = threading.Thread(
                target=self.dead_reckoning_update, args=(data.copy(),))
            self.dead_reckoning_thread.start()
        else:
            logger.debug(f"Vehicle not moving (speed: {speed}mph, gear: {shift_state}), skipping dead reckoning")

    def _handle_valid_gps(self, relevant_data):
        """Persist + send a fresh fix and (re)start interpolation."""
        self.consecutive_no_gps_count = 0
        self.last_known_valid_data = relevant_data.copy()
        self.save_last_position_to_file(self.last_known_valid_data)
        self.send_to_cot(relevant_data)
        if self.config.dead_reckoning_enabled:
            self._start_dead_reckoning(relevant_data.copy())

    def _handle_missing_gps(self):
        """No fresh GPS: keep interpolating / resend the last known position."""
        logger.warning("No valid GPS coordinates from Tesla API")
        if not (self.dead_reckoning_thread and self.dead_reckoning_thread.is_alive()):
            if self.config.dead_reckoning_enabled:
                if self.last_known_valid_data and self.last_known_valid_data.get('speed', 0):
                    logger.info("No GPS - starting dead reckoning based on last known position")
                    self.stop_dead_reckoning.clear()
                    self.dead_reckoning_thread = threading.Thread(
                        target=self.dead_reckoning_update,
                        args=(self.last_known_valid_data.copy(),))
                    self.dead_reckoning_thread.start()
        self.consecutive_no_gps_count += 1
        logger.warning(f"No valid GPS data available (count: {self.consecutive_no_gps_count})")
        if self.last_known_valid_data:
            logger.debug("Using last known position")
            self.send_to_cot(self.last_known_valid_data)

    @staticmethod
    def _has_coordinates(data):
        """True when both coordinates are present (0.0 is a valid coordinate)."""
        return data.get('latitude') is not None and data.get('longitude') is not None

    def _poll_once(self, vehicle):
        """Run one tracking iteration: fetch, process, and sleep one interval."""
        try:
            vehicle_data = vehicle.get_vehicle_data(endpoints=_LOOP_ENDPOINTS)
            self.save_debug_capture(vehicle_data, "vehicle_data")
            if self.consecutive_errors > 0 or self.rate_limit_backoff > 1:
                logger.info("API responding normally again. Resetting backoff.")
                self.consecutive_errors = 0
                self.rate_limit_backoff = 1
        except Exception as e:
            time.sleep(self._handle_api_error(e))
            return

        relevant_data = map_vehicle_data(vehicle_data, vehicle)
        speed = relevant_data.get('speed', 0)
        speed_display = f"{speed}mph" if speed is not None else "0mph"
        dr_status = "ENABLED" if self.config.dead_reckoning_enabled else "DISABLED"
        ap_state = relevant_data.get('autopilot_state')
        if ap_state is None and relevant_data.get('shift_state') in ['D', 'R']:
            logger.warning("autopilot_state field not available in Tesla API response - FSD detection may not work")
        logger.info(f"Got vehicle data: lat={relevant_data.get('latitude')}, lon={relevant_data.get('longitude')}, speed={speed_display}, battery={relevant_data.get('battery_level')}%, autopilot_state={ap_state}, UID={relevant_data.get('UID')}, dead_reckoning={dr_status}")

        if self._has_coordinates(relevant_data):
            self._handle_valid_gps(relevant_data)
        else:
            self._handle_missing_gps()

        time.sleep(self.config.api_loop_delay)

    def fetch_and_send_data_for_vehicle(self, vehicle):  # pragma: no cover - infinite supervisor loop
        """Main loop: fetch from the Tesla API and forward to TAK until the process exits."""
        self.consecutive_no_gps_count = 0
        if not self._seed_initial_position(vehicle):
            return
        while True:
            try:
                self._poll_once(vehicle)
            except Exception as e:
                logger.error(f"Error fetching vehicle data: {e}")
                time.sleep(self.config.api_loop_delay)
