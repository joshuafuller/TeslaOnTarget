#!/usr/bin/env python3
"""
Analyze Tesla API structure from a captured response
"""
import json
import sys
import teslapy

def main():
    if len(sys.argv) < 2:
        print("Usage: python3 analyze_tesla_api.py <capture_file.json>")
        sys.exit(1)
        
    # Load the capture file
    with open(sys.argv[1], 'r') as f:
        data = json.load(f)
    
    # Get the raw API response
    raw_response = data.get('raw_api_response', {})
    
    # Try to decode using TeslaPy's methods
    try:
        # Create a mock vehicle object with the raw data
        class MockVehicle:
            def __init__(self, data):
                self.data = data
                
        vehicle = MockVehicle(raw_response)
        
        # Try to decode the cached_data if it exists
        if 'cached_data' in raw_response:
            print("Found cached_data - this appears to be an encoded response")
            print("\nTrying to decode with TeslaPy...")
            
            # Import TeslaPy's decode methods
            from teslapy import Vehicle
            
            # Create a proper vehicle object
            decoded = Vehicle.decode(raw_response)
            
            print("\nDecoded data structure:")
            print_structure(decoded)
            
            # Look for FSD/Autopilot fields
            print("\n=== FSD/Autopilot Related Fields ===")
            find_fsd_fields(decoded)
            
    except Exception as e:
        print(f"Could not decode with TeslaPy: {e}")
        print("\nRaw response structure:")
        print_structure(raw_response)

def print_structure(obj, prefix="", max_depth=5, current_depth=0):
    """Print the structure of an object."""
    if current_depth >= max_depth:
        return
        
    if isinstance(obj, dict):
        for key, value in obj.items():
            if isinstance(value, (dict, list)):
                print(f"{prefix}{key}: {type(value).__name__}")
                print_structure(value, prefix + "  ", max_depth, current_depth + 1)
            else:
                print(f"{prefix}{key}: {type(value).__name__} = {repr(value)[:100]}")
    elif isinstance(obj, list) and obj:
        print(f"{prefix}[0]: {type(obj[0]).__name__}")
        if isinstance(obj[0], (dict, list)):
            print_structure(obj[0], prefix + "  ", max_depth, current_depth + 1)

def find_fsd_fields(obj, path=""):
    """Recursively find FSD/Autopilot related fields."""
    if isinstance(obj, dict):
        for key, value in obj.items():
            key_lower = str(key).lower()
            if any(word in key_lower for word in ['auto', 'pilot', 'fsd', 'self', 'steer', 'navigate']):
                print(f"{path}.{key}: {value}")
            if isinstance(value, dict):
                find_fsd_fields(value, f"{path}.{key}")

if __name__ == "__main__":
    main()