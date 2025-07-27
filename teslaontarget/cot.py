"""Cursor on Target (CoT) message generation and handling."""

import xml.etree.ElementTree as ET
from datetime import datetime, timezone, timedelta
import hashlib
import logging

logger = logging.getLogger(__name__)


def celsius_to_fahrenheit(celsius):
    """Convert Celsius to Fahrenheit."""
    if celsius is None:
        return None
    return (celsius * 9/5) + 32


def generate_cot_packet(data):
    """Generate a Cursor on Target (CoT) XML packet from vehicle data.
    
    Args:
        data: Dictionary containing vehicle information
        
    Returns:
        str: Formatted CoT XML message
    """
    # Create the root event element
    root = ET.Element("event")
    root.set("version", "2.0")
    root.set("uid", data.get("UID", "Tesla-Unknown"))
    root.set("type", "a-f-G-E-V-C")  # Friendly ground equipment vehicle civilian
    root.set("how", "m-g")  # Machine-generated
    root.set("access", "Undefined")
    
    # Set timestamps - TAK expects specific format
    now = datetime.now(timezone.utc)
    # Format: 2025-07-27T00:05:00.215Z
    time_format = "%Y-%m-%dT%H:%M:%S.%fZ"
    root.set("time", now.strftime(time_format)[:-4] + "Z")  # Remove extra microseconds
    root.set("start", now.strftime(time_format)[:-4] + "Z")
    stale = now + timedelta(minutes=5)
    root.set("stale", stale.strftime(time_format)[:-4] + "Z")
    
    # Add point element (location)
    point = ET.SubElement(root, "point")
    point.set("lat", str(data.get("latitude", 0)))
    point.set("lon", str(data.get("longitude", 0)))
    
    # Use actual elevation if available, convert meters to feet
    elevation_m = data.get("elevation", 0)
    if elevation_m is None:
        elevation_m = 0
    point.set("hae", f"{elevation_m:.3f}")  # Height above ellipsoid in meters
    
    # GPS accuracy - Tesla doesn't provide this, so use reasonable defaults
    # Use higher accuracy when moving, lower when stationary
    speed = data.get("speed", 0)
    if speed and speed > 1:
        ce = "5.0"  # Better accuracy when GPS is active
    else:
        ce = "12.5"  # Typical stationary GPS accuracy
    point.set("ce", ce)  # Circular error
    point.set("le", "9999999.0")  # Linear error (vertical uncertainty)
    
    # Add detail element
    detail = ET.SubElement(root, "detail")
    
    # Add takv element (ATAK version) - should be first in detail
    takv = ET.SubElement(detail, "takv")
    takv.set("os", "35")  # Android OS version (using 35 like ATAK)
    takv.set("version", "1.0.0 (TeslaOnTarget)")
    takv.set("device", "TESLA " + data.get("vehicle_model", "Model"))
    takv.set("platform", "ATAK-CIV")  # Civilian ATAK compatible
    
    # Add contact element with callsign and endpoint
    contact = ET.SubElement(detail, "contact")
    callsign = data.get("display_name", "Tesla")
    contact.set("endpoint", "*:-1:stcp")  # Standard TAK endpoint
    contact.set("callsign", callsign)
    
    # Add uid element with Droid attribute (ATAK standard)
    uid = ET.SubElement(detail, "uid")
    uid.set("Droid", callsign)
    
    # Add precisionlocation
    precisionlocation = ET.SubElement(detail, "precisionlocation")
    precisionlocation.set("altsrc", "GPS")
    precisionlocation.set("geopointsrc", "GPS")
    
    # Add group element (team assignment)
    group = ET.SubElement(detail, "__group")
    group.set("role", "Team Member")
    group.set("name", "Cyan")  # Default team color
    
    # Add status element - ATAK standard with just battery
    status = ET.SubElement(detail, "status")
    battery_level = data.get("battery_level", 0)
    status.set("battery", str(int(battery_level)))
    
    # Add track element for movement
    track = ET.SubElement(detail, "track")
    heading = data.get("heading", 0)
    if heading is None:
        heading = 0
    track.set("course", f"{heading:.8f}")
    
    # Speed in m/s (CoT standard) - Tesla provides mph, convert to m/s
    speed_mph = data.get("speed", 0)
    if speed_mph is None:
        speed_mph = 0
    # Convert mph to m/s: 1 mph = 0.44704 m/s
    speed_ms = speed_mph * 0.44704
    track.set("speed", f"{speed_ms:.8f}")
    
    # Add remarks with Tesla-specific info
    remarks = ET.SubElement(detail, "remarks")
    charge_state = data.get("charging_state", "Disconnected")
    sentry_mode = data.get("sentry_mode", False)
    locked = data.get("locked")
    shift_state = data.get("shift_state", "P")
    battery_range = data.get("battery_range")
    is_climate_on = data.get("is_climate_on", False)
    charge_port_open = data.get("charge_port_door_open", False)
    
    # Check for open windows/trunks
    windows_open = []
    if data.get("fd_window", 0) > 0: windows_open.append("FD")
    if data.get("fp_window", 0) > 0: windows_open.append("FP")
    if data.get("rd_window", 0) > 0: windows_open.append("RD")
    if data.get("rp_window", 0) > 0: windows_open.append("RP")
    
    frunk_open = data.get("ft", 0) > 0
    trunk_open = data.get("rt", 0) > 0
    
    # Autopilot/FSD status
    autopilot_state = data.get("autopilot_state", 0)
    autopilot_style = data.get("autopilot_style")
    
    # Build remarks as a single line with separators for TAK compatibility
    remarks_text = f"Tesla {data.get('vehicle_model', 'Vehicle')}"
    
    # Always show gear state
    if shift_state:
        remarks_text += f" | Gear: {shift_state}"
    else:
        remarks_text += " | Gear: P"  # Default to Park if unknown
    
    # Show range if available
    if battery_range is not None:
        remarks_text += f" | Range: {battery_range:.0f} mi"
    
    # Show if actively charging with time remaining
    if charge_state not in ["Disconnected", "Complete", None]:
        remarks_text += f" | {charge_state}"
        
        # Get charging time info
        charge_limit_soc = data.get("charge_limit_soc", 80)
        minutes_to_full = data.get("minutes_to_full_charge", 0)
        time_to_full = data.get("time_to_full_charge", 0)
        
        # Show time to charge limit
        if minutes_to_full and minutes_to_full > 0:
            hours = int(minutes_to_full // 60)
            mins = int(minutes_to_full % 60)
            if hours > 0:
                remarks_text += f" ({hours}h {mins}m to {charge_limit_soc}%)"
            else:
                remarks_text += f" ({mins}m to {charge_limit_soc}%)"
        elif time_to_full and time_to_full > 0:
            # Fallback to hours if minutes not available
            if time_to_full >= 1:
                remarks_text += f" ({time_to_full:.1f}h to {charge_limit_soc}%)"
            else:
                mins = int(time_to_full * 60)
                remarks_text += f" ({mins}m to {charge_limit_soc}%)"
        
        if charge_port_open:
            remarks_text += " Port Open"
    
    # Show if Autopilot/FSD is engaged when driving
    if shift_state in ["D", "R"] and autopilot_state:
        if autopilot_state == 2:
            remarks_text += " | AUTOPILOT ACTIVE"
        elif autopilot_state == 3:
            remarks_text += " | FSD ACTIVE"
        elif autopilot_state == 1:
            remarks_text += " | AUTOPILOT AVAILABLE"
    
    # Climate status - important to know if someone might be in vehicle
    if is_climate_on:
        remarks_text += " | Climate: ON"
    
    # Security info when parked
    if shift_state == "P" or shift_state is None:
        remarks_text += f" | Sentry: {'ON' if sentry_mode else 'OFF'}"
        if locked is not None:
            remarks_text += f" | Doors: {'Locked' if locked else 'Unlocked'}"
        
        # Alert for security concerns
        if windows_open:
            remarks_text += f" | WINDOWS OPEN: {','.join(windows_open)}"
        if frunk_open:
            remarks_text += " | FRUNK OPEN"
        if trunk_open:
            remarks_text += " | TRUNK OPEN"
    
    remarks.text = remarks_text
    
    # Convert to string
    cot_xml = ET.tostring(root, encoding='unicode')
    
    # Debug log the generated CoT
    logger.debug(f"Generated CoT XML: {cot_xml[:200]}...")
    
    return cot_xml


def format_cot_for_tak(cot_xml):
    """Format CoT XML for TAK Protocol Version 0.
    
    Args:
        cot_xml: Raw CoT XML string
        
    Returns:
        bytes: Properly formatted CoT message for TAK
    """
    # TAK Protocol Version 0: XML declaration + newline + CoT + newline
    # Use single quotes to match ATAK format
    xml_declaration = "<?xml version='1.0' encoding='UTF-8' standalone='yes'?>"
    formatted = xml_declaration + cot_xml
    return formatted.encode('utf-8')