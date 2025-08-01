"""Command line interface for TeslaOnTarget."""

import sys
import time
import signal
import logging
import argparse
import threading
from teslapy import Tesla

from .tesla_api import TeslaCoT
from .config_handler import Config

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('teslaontarget.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Global variable for graceful shutdown
running = True


def signal_handler(sig, frame):
    """Handle shutdown signals gracefully."""
    global running
    logger.info("Shutdown signal received")
    running = False


def main():
    """Main entry point for TeslaOnTarget."""
    parser = argparse.ArgumentParser(description='Bridge Tesla vehicles with TAK servers')
    parser.add_argument('--config', help='Path to config.py file')
    parser.add_argument('--debug', action='store_true', help='Enable debug logging')
    args = parser.parse_args()
    
    # Set debug logging if requested
    if args.debug:
        logging.getLogger().setLevel(logging.DEBUG)
    
    # Load configuration
    Config.load_from_file(args.config)
    
    # Validate configuration
    if not Config.validate():
        logger.error("Invalid configuration. Please check config.py")
        sys.exit(1)
    
    # Set up signal handlers
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    logger.info("Starting TeslaOnTarget...")
    
    try:
        # Initialize Tesla API
        tesla = Tesla(Config.TESLA_USERNAME)
        
        # Get vehicles
        vehicles = tesla.vehicle_list()
        if not vehicles:
            logger.error("No vehicles found on Tesla account")
            sys.exit(1)
            
        logger.info(f"Found {len(vehicles)} vehicle(s) on account")
        
        # Filter vehicles if configured
        vehicle_filter = getattr(Config, 'VEHICLE_FILTER', [])
        if vehicle_filter:
            filtered_vehicles = []
            for vehicle in vehicles:
                display_name = vehicle.get('display_name', '')
                vin = vehicle.get('vin', '')
                if display_name in vehicle_filter or vin in vehicle_filter:
                    filtered_vehicles.append(vehicle)
                    logger.info(f"Selected vehicle: {display_name} (VIN: {vin})")
            
            if not filtered_vehicles:
                logger.error(f"No vehicles matched the filter: {vehicle_filter}")
                sys.exit(1)
            
            vehicles = filtered_vehicles
            logger.info(f"Tracking {len(vehicles)} vehicle(s) based on filter")
        else:
            logger.info("No vehicle filter configured - tracking all vehicles")
        
        # Create shared TAK client for all vehicles
        from .tak_client import TAKClient
        shared_tak_client = TAKClient(Config.COT_URL)
        
        # Create threads for each vehicle
        threads = []
        
        # Wake vehicles if needed
        logger.info("Waking up vehicles...")
        for vehicle in vehicles:
            try:
                if vehicle.get("state") == "asleep":
                    logger.info(f"Waking up {vehicle['display_name']}...")
                    vehicle.sync_wake_up()
            except Exception as e:
                logger.warning(f"Could not wake {vehicle['display_name']}: {e}")
        
        # Start tracking threads
        for vehicle in vehicles:
            # Create a separate TeslaCoT instance for each vehicle
            vehicle_id = vehicle.get('vin', vehicle.get('id_s', 'unknown'))
            tesla_cot = TeslaCoT(vehicle_id=vehicle_id, tak_client=shared_tak_client)
            
            logger.info(f"Starting tracking for {vehicle['display_name']} (VIN: {vehicle.get('vin', 'N/A')})")
            thread = threading.Thread(
                target=tesla_cot.fetch_and_send_data_for_vehicle,
                args=(vehicle,),
                daemon=True,
                name=f"Vehicle-{vehicle['display_name']}"
            )
            thread.start()
            threads.append(thread)
            
        logger.info("All tracking threads started")
        logger.info(f"Sending updates every {Config.API_LOOP_DELAY} seconds")
        logger.info("Press Ctrl+C to stop\n")
        
        # Monitor threads
        while running:
            alive_count = sum(1 for t in threads if t.is_alive())
            if alive_count < len(threads):
                logger.warning(f"Only {alive_count}/{len(threads)} threads running")
            time.sleep(5)
            
    except KeyboardInterrupt:
        logger.info("Interrupted by user")
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)
    finally:
        logger.info("TeslaOnTarget stopped")
        
        
if __name__ == '__main__':
    main()