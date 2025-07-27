#!/usr/bin/env python3
"""
Analyze FULL Tesla API captures to discover all available fields and data.
This tool helps identify FSD states and any other data we might be missing.
"""

import json
import os
import sys
from datetime import datetime
from pathlib import Path
from collections import defaultdict

def load_capture(filepath):
    """Load a single capture file."""
    with open(filepath, 'r') as f:
        return json.load(f)

def find_fsd_related_fields(data, path=""):
    """Recursively find any fields that might be related to FSD/Autopilot."""
    fsd_keywords = ['autopilot', 'fsd', 'full_self', 'self_driving', 'navigate', 
                    'summon', 'autopark', 'autosteer', 'cruise', 'tacc', 'ap_state']
    
    results = []
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            # Check if key contains any FSD-related keywords
            if any(keyword in key.lower() for keyword in fsd_keywords):
                results.append({
                    'path': current_path,
                    'value': value,
                    'type': type(value).__name__
                })
            
            # Recurse into nested structures
            if isinstance(value, (dict, list)):
                results.extend(find_fsd_related_fields(value, current_path))
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                results.extend(find_fsd_related_fields(item, current_path))
    
    return results

def extract_all_fields(data, path=""):
    """Extract all fields and their paths from nested data structure."""
    fields = {}
    
    if isinstance(data, dict):
        for key, value in data.items():
            current_path = f"{path}.{key}" if path else key
            
            if isinstance(value, (dict, list)):
                fields.update(extract_all_fields(value, current_path))
            else:
                fields[current_path] = value
    
    elif isinstance(data, list):
        for i, item in enumerate(data):
            current_path = f"{path}[{i}]"
            if isinstance(item, (dict, list)):
                fields.update(extract_all_fields(item, current_path))
            else:
                fields[current_path] = item
    
    return fields

def compare_captures(captures):
    """Compare captures to find fields that change when FSD is engaged."""
    if len(captures) < 2:
        return []
    
    # Extract all fields from each capture
    all_fields = []
    for capture in captures:
        vehicle_data = capture.get('raw_api_response', capture.get('vehicle_data', {}))
        fields = extract_all_fields(vehicle_data)
        all_fields.append(fields)
    
    # Find fields that change between captures
    changing_fields = defaultdict(list)
    
    all_keys = set()
    for fields in all_fields:
        all_keys.update(fields.keys())
    
    for key in all_keys:
        values = []
        for i, fields in enumerate(all_fields):
            values.append(fields.get(key, 'NOT_PRESENT'))
        
        # Check if values change
        unique_values = list(set(str(v) for v in values))
        if len(unique_values) > 1:
            changing_fields[key] = values
    
    return changing_fields

def main():
    """Main analysis function."""
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
    print("=" * 80)
    
    # Load all captures
    captures = []
    for capture_file in capture_files:
        try:
            data = load_capture(capture_file)
            captures.append(data)
        except Exception as e:
            print(f"Error loading {capture_file}: {e}")
    
    # Part 1: Show ALL available fields from the first capture
    print("\n=== ALL AVAILABLE FIELDS IN TESLA API ===")
    if captures:
        first_capture = captures[0]
        vehicle_data = first_capture.get('raw_api_response', first_capture.get('vehicle_data', {}))
        all_fields = extract_all_fields(vehicle_data)
        
        # Group by category
        categories = defaultdict(list)
        for field_path, value in sorted(all_fields.items()):
            category = field_path.split('.')[0]
            categories[category].append((field_path, value))
        
        for category, fields in sorted(categories.items()):
            print(f"\n[{category.upper()}]")
            for field_path, value in fields[:10]:  # Show first 10 of each category
                print(f"  {field_path}: {value}")
            if len(fields) > 10:
                print(f"  ... and {len(fields) - 10} more fields")
    
    # Part 2: Find FSD/Autopilot related fields
    print("\n\n=== FSD/AUTOPILOT RELATED FIELDS ===")
    all_fsd_fields = set()
    
    for i, capture in enumerate(captures):
        vehicle_data = capture.get('raw_api_response', capture.get('vehicle_data', {}))
        fsd_fields = find_fsd_related_fields(vehicle_data)
        
        for field in fsd_fields:
            field_str = f"{field['path']}: {field['value']}"
            if field_str not in all_fsd_fields:
                all_fsd_fields.add(field_str)
                print(field_str)
    
    # Part 3: Find changing fields (potential FSD indicators)
    print("\n\n=== FIELDS THAT CHANGE BETWEEN CAPTURES ===")
    print("(These might indicate FSD engagement or other state changes)")
    
    changing_fields = compare_captures(captures)
    
    # Filter to interesting changes (exclude obvious ones like location, speed, timestamp)
    exclude_patterns = ['timestamp', 'latitude', 'longitude', 'speed', 'heading', 
                       'battery_level', 'native_location_supported', 'gps_as_of']
    
    interesting_changes = {}
    for field, values in changing_fields.items():
        if not any(pattern in field.lower() for pattern in exclude_patterns):
            interesting_changes[field] = values
    
    # Show top 20 most interesting changing fields
    for field, values in list(interesting_changes.items())[:20]:
        print(f"\n{field}:")
        for i, value in enumerate(values[:5]):  # Show first 5 values
            print(f"  Capture {i}: {value}")
        if len(values) > 5:
            print(f"  ... and {len(values) - 5} more captures")
    
    # Part 4: Specific FSD analysis
    print("\n\n=== SPECIFIC FSD STATE ANALYSIS ===")
    for i, capture in enumerate(captures):
        metadata = capture.get('capture_metadata', {})
        vehicle_data = capture.get('raw_api_response', capture.get('vehicle_data', {}))
        
        drive_state = vehicle_data.get('drive_state', {})
        vehicle_state = vehicle_data.get('vehicle_state', {})
        
        print(f"\nCapture {i} ({metadata.get('datetime', 'Unknown time')}):")
        print(f"  Speed: {drive_state.get('speed')} mph")
        print(f"  Gear: {drive_state.get('shift_state')}")
        
        # Look for ANY autopilot/FSD related fields
        for key, value in vehicle_state.items():
            if 'autopilot' in key.lower() or 'fsd' in key.lower():
                print(f"  {key}: {value}")

if __name__ == "__main__":
    main()