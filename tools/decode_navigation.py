#!/usr/bin/env python3
import json
import base64

# Load navigation response
with open('tesla_api_captures/navigation_route_20250726_205140_868378.json', 'r') as f:
    data = json.load(f)

response = data['raw_api_response']['response']
print("Navigation API Response:")
print(json.dumps(response, indent=2))

# The 'reason' field looks like base64
if 'reason' in response:
    try:
        decoded = base64.b64decode(response['reason'])
        print(f"\nDecoded 'reason' (raw bytes): {decoded}")
        print(f"Decoded 'reason' (hex): {decoded.hex()}")
        
        # Try to parse as protobuf or other format
        print(f"\nLength: {len(decoded)} bytes")
        
        # Check if it's readable text
        try:
            text = decoded.decode('utf-8', errors='ignore')
            print(f"As text (UTF-8): {repr(text)}")
        except:
            pass
            
    except Exception as e:
        print(f"Error decoding: {e}")

# Let's also check if the NAVIGATION_ROUTE endpoint needs parameters
print("\n\n=== CHECKING TESLAPY NAVIGATION IMPLEMENTATION ===")

# Import sys and add TeslaPy path
import sys
sys.path.insert(0, '/mnt/d/development/my_projects/joshuafuller_repos/TeslaPy')

try:
    with open('/mnt/d/development/my_projects/joshuafuller_repos/TeslaPy/teslapy/__init__.py', 'r') as f:
        content = f.read()
        
    # Search for navigation-related methods
    lines = content.split('\n')
    in_navigation = False
    for i, line in enumerate(lines):
        if 'navigation' in line.lower() or 'route' in line.lower():
            # Print context
            start = max(0, i-2)
            end = min(len(lines), i+3)
            for j in range(start, end):
                print(f"{j+1}: {lines[j]}")
            print()
except Exception as e:
    print(f"Error reading TeslaPy: {e}")