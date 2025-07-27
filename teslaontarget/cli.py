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
import os

# Determine log file path - use /logs if available (Docker), otherwise current directory
log_handlers = [logging.StreamHandler()]  # Always log to stdout

# Try to add file handler
try:
    if os.path.exists('/logs') and os.access('/logs', os.W_OK):
        log_path = '/logs/teslaontarget.log'
    else:
        log_path = 'teslaontarget.log'
    
    file_handler = logging.FileHandler(log_path)
    log_handlers.append(file_handler)
except (IOError, OSError) as e:
    # If we can't write to file, just use stdout
    print(f"Warning: Unable to create log file: {e}. Logging to stdout only.")

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=log_handlers
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
            
        logger.info(f"Found {len(vehicles)} vehicle(s)")
        
        # Create threads for each vehicle
        threads = []
        tesla_cot = TeslaCoT()
        
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
            logger.info(f"Starting tracking for {vehicle['display_name']}")
            thread = threading.Thread(
                target=tesla_cot.fetch_and_send_data_for_vehicle,
                args=(vehicle,),
                daemon=True
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