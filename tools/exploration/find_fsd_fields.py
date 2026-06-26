#!/usr/bin/env python3
"""
Find FSD/Autopilot related fields in Tesla API captures
"""
import json
import os
import sys
from collections import defaultdict

def find_autopilot_fields(captures_dir):
    """Search all captures for autopilot/FSD related fields."""
    
    autopilot_fields = defaultdict(set)
    field_values = defaultdict(set)
    
    # Keywords to search for
    keywords = ['autopilot', 'fsd', 'self_driving', 'ap_', 'autosteer', 'navigate', 'smart_summon']
    
    capture_files = [f for f in os.listdir(captures_dir) if f.endswith('.json')]
    
    print(f"Analyzing {len(capture_files)} capture files...")
    
    for filename in capture_files:
        filepath = os.path.join(captures_dir, filename)
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            # Get the API response
            api_response = data.get('raw_api_response', {})
            if not api_response:
                continue
                
            # Search through all response sections
            for section_name, section_data in api_response.items():
                if isinstance(section_data, dict):
                    search_dict_for_keywords(section_data, section_name, keywords, autopilot_fields, field_values)
                    
        except Exception as e:
            print(f"Error reading {filename}: {e}")
    
    # Print findings
    print("\n=== Autopilot/FSD Related Fields Found ===\n")
    
    for section, fields in sorted(autopilot_fields.items()):
        print(f"\n{section}:")
        for field in sorted(fields):
            values = field_values[f"{section}.{field}"]
            print(f"  {field}: {sorted(values)}")

def search_dict_for_keywords(d, path, keywords, autopilot_fields, field_values, max_depth=10):
    """Recursively search dictionary for keyword matches."""
    if max_depth <= 0:
        return
        
    if not isinstance(d, dict):
        return
        
    for key, value in d.items():
        # Check if key contains any keyword
        key_lower = str(key).lower()
        if any(kw in key_lower for kw in keywords):
            autopilot_fields[path].add(key)
            field_values[f"{path}.{key}"].add(str(value))
        
        # Recursively search nested dicts
        if isinstance(value, dict):
            search_dict_for_keywords(value, f"{path}.{key}", keywords, autopilot_fields, field_values, max_depth-1)
        elif isinstance(value, list):
            for i, item in enumerate(value):
                if isinstance(item, dict):
                    search_dict_for_keywords(item, f"{path}.{key}[{i}]", keywords, autopilot_fields, field_values, max_depth-1)

if __name__ == "__main__":
    captures_dir = sys.argv[1] if len(sys.argv) > 1 else "tesla_api_captures"
    find_autopilot_fields(captures_dir)