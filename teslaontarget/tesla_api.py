import json
from collections import deque
import time
import socket
import xml.etree.ElementTree as ET
from urllib.parse import urlparse
import hashlib
import threading
from math import radians, cos, sin
import logging
import re
import os
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Import from new package structure
from .config_handler import Config
from .utils import calculate_distance, save_json_file, load_json_file
from .cot import generate_cot_packet, format_cot_for_tak
from .tak_client import TAKClient

class TeslaCoT:
    def __init__(self):
        # Load configuration
        Config.load_from_file()
        self.config = Config
        
        self.last_known_valid_data = self.read_last_position_from_file()
        self.positions_queue = deque(maxlen=2)
        self.vehicle_uids = {}
        self.dead_reckoning_thread = None
        self.stop_dead_reckoning = threading.Event()
        self.tak_client = TAKClient(self.config.COT_URL)
        self.tesla = None
        self.vehicle = None
        
        # Rate limiting tracking
        self.rate_limit_backoff = 1  # Multiplier for delays
        self.consecutive_errors = 0
        self.last_rate_limit_time = 0
        
        # Debug mode - captures all Tesla API responses
        self.debug_mode = getattr(self.config, 'DEBUG_MODE', True)  # Default to True for now
        self.debug_dir = "tesla_api_captures"
        self.capture_count = 0
        if self.debug_mode:
            os.makedirs(self.debug_dir, exist_ok=True)
            logger.info(f"DEBUG MODE ENABLED! All Tesla API responses will be captured to {self.debug_dir}/")
        
    def read_last_position_from_file(self):
        """Read the last known position from file."""
        return load_json_file(self.config.LAST_POSITION_FILE)
    
    def save_last_position_to_file(self, data):
        """Save the current position to file."""
        try:
            save_json_file(self.config.LAST_POSITION_FILE, data)
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
    
    def extract_relevant_data(self, vehicle_data, vehicle):
        """Extract relevant data from Tesla API response."""
        drive_state = vehicle_data.get("drive_state", {})
        charge_state = vehicle_data.get("charge_state", {})
        vehicle_state = vehicle_data.get("vehicle_state", {})
        climate_state = vehicle_data.get("climate_state", {})
        vehicle_config = vehicle_data.get("vehicle_config", {})
        
        # Generate unique ID for this vehicle
        vehicle_id = vehicle.get("id_s", vehicle.get("vehicle_id", "unknown"))
        uid = f"TESLA-{hashlib.md5(str(vehicle_id).encode()).hexdigest()[:8]}"
        
        # Get vehicle model from config
        display_name = vehicle.get("display_name", "Tesla")
        
        # Build detailed model string from vehicle config
        car_type = vehicle_config.get("car_type", "")
        year = vehicle_config.get("year", "")
        trim = vehicle_config.get("trim_badging", "")
        
        # Map car types to model names
        model_map = {
            "models": "Model S",
            "modelx": "Model X",
            "model3": "Model 3",
            "modely": "Model Y",
            "cybertruck": "Cybertruck"
        }
        
        model_name = model_map.get(car_type.lower(), car_type)
        
        # Parse trim badging - common codes:
        # p = Performance, l = Long Range, s = Standard Range
        # 74 = 2024, 73 = 2023, etc.
        # d = Dual Motor (AWD), s = Single Motor (RWD)
        if trim:
            # For Model Y Performance, p74d might not be year-related
            # Check if vehicle_config has explicit year
            if not year:
                # If year not provided, don't show it
                pass  # Will just show "Model Y Performance"
            
            # Determine variant
            if trim.lower().startswith('p'):
                variant = "Performance"
            elif trim.lower().startswith('l'):
                variant = "Long Range"
            else:
                variant = trim.upper()
                
            vehicle_model = f"{model_name} {variant}"
        else:
            vehicle_model = model_name
            
        if year:
            vehicle_model = f"{year} {vehicle_model}"
        
        data = {
            "UID": uid,
            "latitude": drive_state.get("latitude"),
            "longitude": drive_state.get("longitude"),
            "speed": drive_state.get("speed", 0),
            "heading": drive_state.get("heading", 0),
            "elevation": drive_state.get("native_location_supported", 0),  # Tesla doesn't provide elevation
            "battery_level": charge_state.get("battery_level", 0),
            "charging_state": charge_state.get("charging_state", "Disconnected"),
            "vehicle_name": vehicle_state.get("vehicle_name", display_name),
            "display_name": display_name,
            "vehicle_model": vehicle_model,
            "inside_temp": climate_state.get("inside_temp"),
            "outside_temp": climate_state.get("outside_temp"),
            "sentry_mode": vehicle_state.get("sentry_mode", False),
            "locked": vehicle_state.get("locked", None),
            "shift_state": drive_state.get("shift_state"),  # P, D, R, N
            "battery_range": charge_state.get("battery_range"),  # Miles remaining
            "is_climate_on": climate_state.get("is_climate_on", False),
            "charge_port_door_open": charge_state.get("charge_port_door_open", False),
            # Charging time info
            "time_to_full_charge": charge_state.get("time_to_full_charge", 0),  # Hours to 100%
            "charge_limit_soc": charge_state.get("charge_limit_soc", 80),  # Target charge %
            "minutes_to_full_charge": charge_state.get("minutes_to_full_charge", 0),  # Minutes to target
            # Window positions (0 = closed, >0 = open)
            "fd_window": vehicle_state.get("fd_window", 0),  # Front driver
            "fp_window": vehicle_state.get("fp_window", 0),  # Front passenger
            "rd_window": vehicle_state.get("rd_window", 0),  # Rear driver
            "rp_window": vehicle_state.get("rp_window", 0),  # Rear passenger
            "ft": vehicle_state.get("ft", 0),  # Front trunk (frunk)
            "rt": vehicle_state.get("rt", 0),  # Rear trunk
            # Autopilot/FSD status
            # Note: Tesla API may not always provide autopilot_state
            "autopilot_state": vehicle_state.get("autopilot_state", 0),
            "autopilot_style": vehicle_state.get("autopilot_style"),
            "autopark_state": vehicle_state.get("autopark_state_v3"),
            "timestamp": time.time()
        }
        
        return data
    
    def send_to_cot(self, data):
        """Send data to TAK server via CoT."""
        try:
            cot_packet = generate_cot_packet(data)
            cot_bytes = format_cot_for_tak(cot_packet)
            
            logger.info(f"Sending CoT for {data.get('display_name')} at {data.get('latitude')}, {data.get('longitude')}")
            
            if self.tak_client.send_cot(cot_bytes):
                logger.info(f"Successfully sent CoT packet for {data.get('vehicle_name', 'Unknown')} ({len(cot_bytes)} bytes)")
            else:
                logger.warning("Failed to send CoT packet")
        except Exception as e:
            logger.error(f"Error sending CoT packet: {e}", exc_info=True)
    
    def dead_reckoning_update(self, initial_data):
        """Perform dead reckoning interpolation between Tesla API updates."""
        start_time = time.time()
        max_duration = self.config.API_LOOP_DELAY - 1  # Run for slightly less than API interval
        
        # Keep track of current position
        current_lat = initial_data.get('latitude')
        current_lon = initial_data.get('longitude')
        
        logger.info(f"Dead reckoning started for up to {max_duration}s from lat={current_lat:.6f}, lon={current_lon:.6f}")
        
        update_count = 0
        while not self.stop_dead_reckoning.is_set():
            if current_lat and current_lon:
                # Wait for the next update interval
                time.sleep(self.config.DEAD_RECKONING_DELAY)
                
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
                speed_ms = speed * self.config.MPH_TO_MS
                heading = initial_data.get('heading', 0)
                if heading is None:
                    heading = 0
                heading_rad = radians(heading)
                
                # Calculate distance traveled in one update cycle
                distance = speed_ms * self.config.DEAD_RECKONING_DELAY
                
                # Calculate new position from current position
                lat_rad = radians(current_lat)
                lon_rad = radians(current_lon)
                
                # Earth radius in meters
                R = 6371000
                
                # Calculate new latitude
                new_lat_rad = lat_rad + (distance / R) * cos(heading_rad)
                
                # Calculate new longitude
                new_lon_rad = lon_rad + (distance / (R * cos(lat_rad))) * sin(heading_rad)
                
                # Convert back to degrees
                current_lat = new_lat_rad * 180 / 3.14159265359
                current_lon = new_lon_rad * 180 / 3.14159265359
                
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
    
    def fetch_and_send_data_for_vehicle(self, vehicle):
        """Main loop to fetch data from Tesla API and send to TAK."""
        # Generate a hashed UID for the vehicle based on its VIN
        vehicle_data = None
        vehicle_id = None
        wake_attempts = 0
        max_wake_attempts = 3
        
        # Initial setup - try to get vehicle data
        logger.info(f"Initializing tracking for {vehicle.get('display_name', 'Unknown')}...")
        
        # First check if vehicle is asleep
        if vehicle.get("state") == "asleep":
            logger.info(f"Vehicle is asleep. Attempting to wake for initial position...")
            try:
                vehicle.sync_wake_up()
                logger.info("Vehicle wake command sent, waiting for it to come online...")
                time.sleep(5)  # Give it a moment to wake up
            except Exception as e:
                logger.warning(f"Failed to wake vehicle: {e}")
        
        # Now try to get vehicle data
        while vehicle_data is None and wake_attempts < max_wake_attempts:
            try:
                # Tesla API now requires specific endpoints to get location data
                # Using all available endpoints to capture complete data
                vehicle_data = vehicle.get_vehicle_data(endpoints='location_data;drive_state;charge_state;vehicle_state;climate_state;vehicle_config;gui_settings')
                vehicle_id = vehicle_data.get("vin", 
                                             vehicle_data.get("vehicle_state", {}).get("vehicle_name"))
                logger.info(f"Successfully got initial vehicle data")
                
                # Save debug capture of initial data
                self.save_debug_capture(vehicle_data, "initial_vehicle_data")
            except Exception as e:
                wake_attempts += 1
                logger.warning(f"Failed to get vehicle data (attempt {wake_attempts}/{max_wake_attempts}): {e}")
                if wake_attempts < max_wake_attempts:
                    time.sleep(10)  # Wait before retry
        
        if vehicle_data is None:
            logger.error(f"Failed to get initial vehicle data after {max_wake_attempts} attempts")
            # Try to use cached position if available
            if self.last_known_valid_data:
                logger.info("Using cached position data")
                vehicle_id = vehicle.get('vin', vehicle.get('id_s', 'unknown'))
                # Send cached position immediately
                self.send_to_cot(self.last_known_valid_data)
            else:
                logger.error(f"No cached data available for {vehicle.get('display_name', 'Unknown')}")
                return
        else:
            # Extract initial data to save position
            initial_data = self.extract_relevant_data(vehicle_data, vehicle)
            if initial_data.get('latitude') and initial_data.get('longitude'):
                self.last_known_valid_data = initial_data
                self.save_last_position_to_file(initial_data)
                logger.info(f"Saved initial position: {initial_data.get('latitude')}, {initial_data.get('longitude')}")
        
        # Main loop
        consecutive_no_gps_count = 0
        vehicle_woken_once = True  # We already woke it in initialization
        
        while True:
            try:
                # Check if vehicle needs to be woken (only if we haven't woken it yet)
                if not vehicle_woken_once:
                    # Get fresh vehicle state
                    vehicle_list = vehicle._owner.vehicle_list()
                    for v in vehicle_list:
                        if v['id'] == vehicle['id']:
                            if v.get('state') == 'asleep':
                                logger.info(f"Vehicle {vehicle.get('display_name')} is asleep. Waking for initial position...")
                                try:
                                    vehicle.sync_wake_up()
                                    vehicle_woken_once = True
                                    logger.info("Vehicle woken successfully")
                                except Exception as e:
                                    logger.warning(f"Failed to wake vehicle: {e}")
                            break
                
                # Try to get vehicle data
                try:
                    vehicle_data = vehicle.get_vehicle_data(endpoints='location_data;drive_state;charge_state;vehicle_state;climate_state;vehicle_config')
                    
                    # Save debug capture
                    self.save_debug_capture(vehicle_data, "vehicle_data")
                    
                    # Reset rate limiting on success
                    if self.consecutive_errors > 0 or self.rate_limit_backoff > 1:
                        logger.info(f"API responding normally again. Resetting backoff.")
                        self.consecutive_errors = 0
                        self.rate_limit_backoff = 1
                        
                except Exception as e:
                    error_str = str(e).lower()
                    
                    # Check for rate limiting indicators
                    if any(indicator in error_str for indicator in ['429', 'rate limit', 'too many requests', 'timeout']):
                        self.consecutive_errors += 1
                        self.rate_limit_backoff = min(self.rate_limit_backoff * 2, 32)  # Max 32x backoff
                        self.last_rate_limit_time = time.time()
                        
                        delay = self.config.API_LOOP_DELAY * self.rate_limit_backoff
                        logger.warning(f"Rate limit detected! Backing off to {delay}s delay (error #{self.consecutive_errors})")
                        logger.warning(f"Error details: {e}")
                        
                        # Send cached position to keep TAK updated
                        if self.last_known_valid_data:
                            self.send_to_cot(self.last_known_valid_data)
                            
                        time.sleep(delay)
                        continue
                        
                    elif "vehicle unavailable" in error_str or "asleep" in error_str:
                        logger.info(f"Vehicle is asleep/unavailable. Using last known position.")
                        if self.last_known_valid_data:
                            self.send_to_cot(self.last_known_valid_data)
                        else:
                            logger.warning("No last known position available")
                        time.sleep(self.config.API_LOOP_DELAY)
                        continue
                    else:
                        # Other errors - log and continue
                        self.consecutive_errors += 1
                        logger.error(f"API error (#{self.consecutive_errors}): {e}")
                        
                        # If we're getting repeated errors, start backing off
                        if self.consecutive_errors >= 3:
                            self.rate_limit_backoff = min(self.rate_limit_backoff * 1.5, 16)
                            delay = self.config.API_LOOP_DELAY * self.rate_limit_backoff
                            logger.warning(f"Multiple API errors detected. Backing off to {delay}s delay")
                            time.sleep(delay)
                        else:
                            time.sleep(self.config.API_LOOP_DELAY)
                        continue
                
                relevant_data = self.extract_relevant_data(vehicle_data, vehicle)
                
                # Log key data including speed and FSD status for debugging
                speed = relevant_data.get('speed', 0)
                speed_display = f"{speed}mph" if speed is not None else "0mph"
                dr_status = "ENABLED" if getattr(self.config, 'DEAD_RECKONING_ENABLED', False) else "DISABLED"
                
                # Check if autopilot_state is available
                ap_state = relevant_data.get('autopilot_state')
                if ap_state is None and relevant_data.get('shift_state') in ['D', 'R']:
                    logger.warning("autopilot_state field not available in Tesla API response - FSD detection may not work")
                
                logger.info(f"Got vehicle data: lat={relevant_data.get('latitude')}, lon={relevant_data.get('longitude')}, speed={speed_display}, battery={relevant_data.get('battery_level')}%, autopilot_state={ap_state}, UID={relevant_data.get('UID')}, dead_reckoning={dr_status}")
                
                
                # Check if we have valid GPS data
                if relevant_data.get('latitude') and relevant_data.get('longitude'):
                    consecutive_no_gps_count = 0  # Reset counter
                    
                    # Save valid position
                    self.last_known_valid_data = relevant_data.copy()
                    self.save_last_position_to_file(self.last_known_valid_data)
                    
                    # Send current position
                    self.send_to_cot(relevant_data)
                    
                    # Start or restart dead reckoning for interpolation between GPS updates
                    if getattr(self.config, 'DEAD_RECKONING_ENABLED', False):
                        # Stop existing dead reckoning thread if running
                        if self.dead_reckoning_thread and self.dead_reckoning_thread.is_alive():
                            logger.debug("Restarting dead reckoning with new position")
                            self.stop_dead_reckoning.set()
                            self.dead_reckoning_thread.join(timeout=1)
                        
                        # Start dead reckoning if vehicle is moving OR if shift state is D/R
                        speed = relevant_data.get('speed', 0)
                        shift_state = relevant_data.get('shift_state')
                        if (speed is not None and speed > 0) or shift_state in ['D', 'R']:
                            logger.info(f"Starting dead reckoning interpolation (speed: {speed}mph, gear: {shift_state})")
                            self.stop_dead_reckoning.clear()
                            self.dead_reckoning_thread = threading.Thread(
                                target=self.dead_reckoning_update,
                                args=(relevant_data.copy(),)
                            )
                            self.dead_reckoning_thread.start()
                        else:
                            logger.debug(f"Vehicle not moving (speed: {speed}mph, gear: {shift_state}), skipping dead reckoning")
                else:
                    logger.warning("No valid GPS coordinates from Tesla API")
                    
                    # Continue dead reckoning if already running
                    if not (self.dead_reckoning_thread and self.dead_reckoning_thread.is_alive()):
                        if getattr(self.config, 'DEAD_RECKONING_ENABLED', False):
                            if self.last_known_valid_data and self.last_known_valid_data.get('speed', 0):
                                logger.info("No GPS - starting dead reckoning based on last known position")
                                self.stop_dead_reckoning.clear()
                                self.dead_reckoning_thread = threading.Thread(
                                    target=self.dead_reckoning_update,
                                    args=(self.last_known_valid_data.copy(),)
                                )
                                self.dead_reckoning_thread.start()
                    
                    consecutive_no_gps_count += 1
                    logger.warning(f"No valid GPS data available (count: {consecutive_no_gps_count})")
                    
                    # Don't keep waking the vehicle if it's parked
                    # We already got initial position during setup
                    # Just use the last known position
                    
                    # Use last known position if available
                    if self.last_known_valid_data:
                        logger.debug("Using last known position")
                        # Send last known position to keep it alive in TAK
                        self.send_to_cot(self.last_known_valid_data)
                
                time.sleep(self.config.API_LOOP_DELAY)
                
            except Exception as e:
                logger.error(f"Error fetching vehicle data: {e}")
                time.sleep(self.config.API_LOOP_DELAY)
