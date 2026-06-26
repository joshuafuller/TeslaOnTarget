"""Utility functions for TeslaOnTarget."""

import json
import logging
from math import atan2, cos, radians, sin, sqrt

from .constants import EARTH_RADIUS_M, METERS_TO_FEET, MPH_TO_MS

logger = logging.getLogger(__name__)


def calculate_distance(lat1, lon1, lat2, lon2):
    """Calculate the great circle distance between two points on Earth.
    
    Args:
        lat1, lon1: First point coordinates
        lat2, lon2: Second point coordinates
        
    Returns:
        float: Distance in meters
    """
    R = EARTH_RADIUS_M
    phi1 = radians(lat1)
    phi2 = radians(lat2)
    delta_phi = radians(lat2 - lat1)
    delta_lambda = radians(lon2 - lon1)
    
    a = sin(delta_phi/2) * sin(delta_phi/2) + \
        cos(phi1) * cos(phi2) * \
        sin(delta_lambda/2) * sin(delta_lambda/2)
    c = 2 * atan2(sqrt(a), sqrt(1-a))
    
    return R * c


def load_json_file(filepath):
    """Load JSON data from file.
    
    Args:
        filepath: Path to JSON file
        
    Returns:
        dict: Loaded data or None if error
    """
    try:
        with open(filepath, 'r') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError) as e:
        logger.debug(f"Could not load JSON from {filepath}: {e}")
        return None


def save_json_file(filepath, data):
    """Save data to JSON file.
    
    Args:
        filepath: Path to save file
        data: Data to save
        
    Returns:
        bool: True if successful
    """
    try:
        with open(filepath, 'w') as f:
            json.dump(data, f, indent=2)
        return True
    except Exception as e:
        logger.error(f"Failed to save JSON to {filepath}: {e}")
        return False


def meters_to_feet(meters):
    """Convert meters to feet.
    
    Args:
        meters: Distance in meters
        
    Returns:
        float: Distance in feet
    """
    return meters * METERS_TO_FEET


def mph_to_ms(mph):
    """Convert miles per hour to meters per second.
    
    Args:
        mph: Speed in miles per hour
        
    Returns:
        float: Speed in meters per second
    """
    return mph * MPH_TO_MS if mph else 0


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit.
    
    Args:
        celsius: Temperature in Celsius
        
    Returns:
        float: Temperature in Fahrenheit
    """
    return (celsius * 9/5) + 32 if celsius is not None else None