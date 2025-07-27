#!/usr/bin/env python3
"""
Replay captured Tesla API responses for analysis and debugging.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path

def load_capture(filepath):
    """Load a single capture file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def analyze_capture(data):
    """Analyze a single capture and extract key information."""
    vehicle_data = data.get('vehicle_data', {})
    drive_state = vehicle_data.get('drive_state', {})
    vehicle_state = vehicle_data.get('vehicle_state', {})
    
    analysis = {
        'timestamp': data.get('datetime', 'Unknown'),
        'speed_mph': drive_state.get('speed'),
        'heading': drive_state.get('heading'),
        'shift_state': drive_state.get('shift_state'),
        'latitude': drive_state.get('latitude'),
        'longitude': drive_state.get('longitude'),
        'autopilot_state': vehicle_state.get('autopilot_state'),
        'autopilot_style': vehicle_state.get('autopilot_style'),
    }
    
    return analysis

def main():
    """Main replay function."""
    captures_dir = 'tesla_api_captures'
    
    if not os.path.exists(captures_dir):
        print(f"No captures directory found at {captures_dir}")
        return
    
    # Get all capture files
    capture_files = sorted(Path(captures_dir).glob('*.json'))
    
    if not capture_files:
        print(f"No capture files found in {captures_dir}")
        return
    
    print(f"Found {len(capture_files)} capture files")
    print("-" * 80)
    
    for capture_file in capture_files:
        try:
            data = load_capture(capture_file)
            analysis = analyze_capture(data)
            
            print(f"File: {capture_file.name}")
            print(f"Time: {analysis['timestamp']}")
            print(f"Speed: {analysis['speed_mph']} mph")
            print(f"Gear: {analysis['shift_state']}")
            print(f"Location: {analysis['latitude']}, {analysis['longitude']}")
            print(f"Autopilot State: {analysis['autopilot_state']}")
            print(f"Autopilot Style: {analysis['autopilot_style']}")
            print("-" * 80)
            
        except Exception as e:
            print(f"Error processing {capture_file}: {e}")
    
    # Look for FSD engagement
    print("\n=== AUTOPILOT/FSD ANALYSIS ===")
    fsd_captures = []
    
    for capture_file in capture_files:
        try:
            data = load_capture(capture_file)
            vehicle_data = data.get('vehicle_data', {})
            vehicle_state = vehicle_data.get('vehicle_state', {})
            drive_state = vehicle_data.get('drive_state', {})
            
            autopilot_state = vehicle_state.get('autopilot_state')
            if autopilot_state and autopilot_state > 0:
                fsd_captures.append({
                    'file': capture_file.name,
                    'autopilot_state': autopilot_state,
                    'autopilot_style': vehicle_state.get('autopilot_style'),
                    'speed': drive_state.get('speed'),
                    'gear': drive_state.get('shift_state')
                })
        except:
            pass
    
    if fsd_captures:
        print(f"Found {len(fsd_captures)} captures with Autopilot/FSD active:")
        for capture in fsd_captures:
            print(f"  {capture['file']}: State={capture['autopilot_state']}, Style={capture['autopilot_style']}, Speed={capture['speed']}, Gear={capture['gear']}")
    else:
        print("No captures found with Autopilot/FSD active")

if __name__ == "__main__":
    main()