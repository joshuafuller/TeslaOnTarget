#!/usr/bin/env python3
"""
Discover all available Tesla API fields by querying all endpoints.
This helps find autopilot/FSD fields and other data we might be missing.
"""

import sys
sys.path.insert(0, '/mnt/d/development/my_projects/joshuafuller_repos/TeslaPy')

import teslapy
import json
from pathlib import Path

def main():
    """Query Tesla API with all available endpoints and save the response."""
    
    # Get credentials from config
    config_path = Path(__file__).parent.parent / 'config.py'
    if not config_path.exists():
        print("Error: config.py not found. Please copy config.py.template to config.py")
        return
    
    # Import config
    import importlib.util
    spec = importlib.util.spec_from_file_location("config", config_path)
    config = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(config)
    
    print(f"Connecting to Tesla account: {config.TESLA_USERNAME}")
    
    try:
        # Connect to Tesla
        with teslapy.Tesla(config.TESLA_USERNAME) as tesla:
            vehicles = tesla.vehicle_list()
            
            if not vehicles:
                print("No vehicles found")
                return
            
            vehicle = vehicles[0]
            print(f"Found vehicle: {vehicle.get('display_name')}")
            
            # Wake the vehicle if needed
            if vehicle.get('state') == 'asleep':
                print("Waking vehicle...")
                vehicle.sync_wake_up()
                print("Vehicle is awake")
            
            # Query ALL available endpoints
            all_endpoints = [
                'location_data',
                'charge_state', 
                'climate_state',
                'vehicle_state',
                'gui_settings',
                'vehicle_config',
                'drive_state',
                'mobile_enabled',
                'software_update',
                'speed_limit_mode'
            ]
            
            print(f"\nQuerying all endpoints: {';'.join(all_endpoints)}")
            data = vehicle.get_vehicle_data(endpoints=';'.join(all_endpoints))
            
            # Save full response
            output_file = "tesla_full_api_discovery.json"
            with open(output_file, 'w') as f:
                json.dump(data, f, indent=2)
            
            print(f"\nFull API response saved to: {output_file}")
            
            # Look for autopilot/FSD related fields
            print("\n=== SEARCHING FOR AUTOPILOT/FSD FIELDS ===")
            
            def search_fields(obj, path="", keywords=['autopilot', 'fsd', 'full_self', 'self_driving', 
                                                      'navigate', 'summon', 'autopark', 'autosteer', 
                                                      'cruise', 'tacc', 'ap_']):
                """Recursively search for fields containing keywords."""
                if isinstance(obj, dict):
                    for key, value in obj.items():
                        current_path = f"{path}.{key}" if path else key
                        # Check if key contains any keywords
                        if any(kw in key.lower() for kw in keywords):
                            print(f"  {current_path}: {value}")
                        # Recurse
                        if isinstance(value, (dict, list)):
                            search_fields(value, current_path, keywords)
                elif isinstance(obj, list):
                    for i, item in enumerate(obj):
                        search_fields(item, f"{path}[{i}]", keywords)
            
            search_fields(data)
            
            # Also show some key fields that might help
            print("\n=== KEY VEHICLE STATE FIELDS ===")
            if 'vehicle_state' in data:
                for key, value in sorted(data['vehicle_state'].items()):
                    if any(word in key.lower() for word in ['auto', 'pilot', 'fsd', 'self', 'drive']):
                        print(f"  vehicle_state.{key}: {value}")
            
            print("\n=== KEY DRIVE STATE FIELDS ===")
            if 'drive_state' in data:
                for key, value in sorted(data['drive_state'].items()):
                    print(f"  drive_state.{key}: {value}")
            
    except Exception as e:
        print(f"Error: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    main()