#!/usr/bin/env python3
import json
import glob
import os

# Get the most recent vehicle data capture
captures = glob.glob('tesla_api_captures/vehicle_data_*.json')
latest = max(captures, key=os.path.getctime)

print(f"Checking latest capture: {latest}")
print(f"File time: {os.path.getctime(latest)}")

with open(latest, 'r') as f:
    data = json.load(f)

vehicle_data = data['raw_api_response']

# Search for any navigation-related fields
print("\n=== SEARCHING FOR NAVIGATION/DESTINATION DATA ===\n")

nav_keywords = ['route', 'nav', 'dest', 'waypoint', 'walmart', 'trip', 'journey', 'path', 'share']

def search_dict(d, path='', depth=0):
    """Recursively search for navigation-related fields."""
    if depth > 5:  # Prevent too deep recursion
        return
        
    if isinstance(d, dict):
        for key, value in d.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if key contains navigation keywords
            if any(kw in str(key).lower() for kw in nav_keywords):
                print(f"{current_path}: {value}")
            
            # Also check if value contains walmart or navigation terms
            if value and isinstance(value, str):
                if any(kw in value.lower() for kw in ['walmart', 'navigation', 'destination']):
                    print(f"{current_path}: {value} <-- POSSIBLE DESTINATION!")
            
            # Recurse into nested dicts/lists
            if isinstance(value, dict):
                search_dict(value, current_path, depth+1)
            elif isinstance(value, list) and value:
                for i, item in enumerate(value):
                    if isinstance(item, dict):
                        search_dict(item, f"{current_path}[{i}]", depth+1)

search_dict(vehicle_data)

# Check specific sections that might have navigation
print("\n=== CHECKING SPECIFIC SECTIONS ===\n")

# Check drive_state
drive_state = vehicle_data.get('drive_state', {})
print("drive_state fields:")
for k, v in drive_state.items():
    if v not in [None, False, 0]:
        print(f"  {k}: {v}")

# Check gui_settings
gui_settings = vehicle_data.get('gui_settings', {})
if gui_settings:
    print("\ngui_settings fields:")
    for k, v in gui_settings.items():
        print(f"  {k}: {v}")

# Check if there are any new top-level keys
print("\n=== TOP LEVEL KEYS ===")
for key in sorted(vehicle_data.keys()):
    if key not in ['charge_state', 'climate_state', 'drive_state', 'gui_settings', 'vehicle_config', 'vehicle_state']:
        print(f"  {key}: {type(vehicle_data[key])}")