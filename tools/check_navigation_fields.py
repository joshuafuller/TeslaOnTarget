#!/usr/bin/env python3
import json
import sys

# Load the most recent vehicle data
with open('tesla_api_captures/vehicle_data_20250726_205232_459471.json', 'r') as f:
    data = json.load(f)

vehicle_data = data['raw_api_response']

print("=== SEARCHING FOR NAVIGATION FIELDS ===\n")

# Keywords to search for
keywords = ['route', 'nav', 'dest', 'waypoint', 'gps', 'location', 'target', 'trip']

def search_dict(d, path=''):
    """Recursively search for navigation-related fields."""
    if isinstance(d, dict):
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if key contains navigation keywords
            if any(kw in key.lower() for kw in keywords):
                print(f"{current_path}: {value}")
            
            # Recurse into nested dicts/lists
            if isinstance(value, dict):
                search_dict(value, current_path)
            elif isinstance(value, list) and value and isinstance(value[0], dict):
                for i, item in enumerate(value):
                    search_dict(item, f"{current_path}[{i}]")

search_dict(vehicle_data)

print("\n=== ALL DRIVE_STATE FIELDS ===\n")
drive_state = vehicle_data.get('drive_state', {})
for k, v in sorted(drive_state.items()):
    print(f"drive_state.{k}: {v}")

print("\n=== CHECK GUI_SETTINGS ===\n")
gui_settings = vehicle_data.get('gui_settings', {})
for k, v in sorted(gui_settings.items()):
    if 'nav' in k.lower() or 'route' in k.lower():
        print(f"gui_settings.{k}: {v}")