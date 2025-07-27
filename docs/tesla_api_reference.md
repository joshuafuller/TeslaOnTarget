# Tesla Owner API Reference

This document provides a comprehensive reference for the Tesla Owner API data structure as used in TeslaOnTarget.

## Overview

The Tesla Owner API provides detailed information about your vehicle through various endpoints. When calling `get_vehicle_data()`, you can specify which endpoints to retrieve:

- `location_data` - GPS position only
- `drive_state` - Driving information (speed, heading, location)
- `charge_state` - Battery and charging information
- `climate_state` - HVAC and temperature data
- `vehicle_state` - General vehicle status
- `vehicle_config` - Vehicle configuration
- `gui_settings` - Display settings

## Data Structure

### Vehicle Info
Basic information about the vehicle:

| Field | Type | Description |
|-------|------|-------------|
| `display_name` | string | User-assigned vehicle name |
| `vin` | string | Vehicle Identification Number |
| `id` | integer | Tesla's internal vehicle ID |
| `vehicle_id` | integer | Alternative vehicle ID |
| `state` | string | Vehicle state: "online", "asleep", "offline" |

### Drive State
Location and movement data:

| Field | Type | Description | Used by TeslaOnTarget |
|-------|------|-------------|----------------------|
| `latitude` | float | Current GPS latitude | ✓ |
| `longitude` | float | Current GPS longitude | ✓ |
| `heading` | integer | Direction in degrees (0-360) | ✓ |
| `speed` | integer/null | Speed in mph (null when stopped) | ✓ |
| `power` | integer | Power usage in kW |
| `shift_state` | string/null | "P", "D", "R", "N" or null |
| `gps_as_of` | integer | Unix timestamp of GPS reading |
| `native_latitude` | float | Native GPS latitude |
| `native_longitude` | float | Native GPS longitude |
| `native_location_supported` | integer | 1 if native location supported |
| `native_type` | string | GPS type (e.g., "wgs") |
| `timestamp` | integer | Unix timestamp in milliseconds |

### Charge State
Battery and charging information:

| Field | Type | Description | Used by TeslaOnTarget |
|-------|------|-------------|----------------------|
| `battery_level` | integer | Battery percentage (0-100) | ✓ |
| `charging_state` | string | "Charging", "Disconnected", "Complete", etc. | ✓ |
| `battery_range` | float | Estimated range in miles |
| `charge_rate` | float | Charging speed in mi/hr |
| `charger_power` | integer | Charging power in kW |
| `charge_port_door_open` | boolean | Whether charge port is open |
| `charge_limit_soc` | integer | Charge limit percentage |
| `minutes_to_full_charge` | integer | Time to complete charging |
| `time_to_full_charge` | float | Hours to full charge |
| `charger_voltage` | integer | Charging voltage |
| `charger_actual_current` | integer | Actual charging current |
| `est_battery_range` | float | Estimated range based on driving |

### Climate State
HVAC and temperature data:

| Field | Type | Description |
|-------|------|-------------|
| `inside_temp` | float | Interior temperature in Celsius |
| `outside_temp` | float | Exterior temperature in Celsius |
| `driver_temp_setting` | float | Driver side temperature setting |
| `passenger_temp_setting` | float | Passenger side temperature setting |
| `is_climate_on` | boolean | Whether HVAC is active |
| `is_preconditioning` | boolean | Whether preconditioning is active |
| `battery_heater` | boolean | Whether battery heater is on |
| `fan_status` | integer | Fan speed (0-7) |
| `defrost_mode` | integer | Defrost mode setting |
| `is_front_defroster_on` | boolean | Front defroster status |
| `is_rear_defroster_on` | boolean | Rear defroster status |

### Vehicle State
General vehicle status:

| Field | Type | Description | Used by TeslaOnTarget |
|-------|------|-------------|----------------------|
| `vehicle_name` | string | Same as display_name | ✓ |
| `sentry_mode` | boolean | Whether Sentry Mode is active |
| `locked` | boolean | Door lock status |
| `odometer` | float | Total miles driven |
| `car_version` | string | Software version |
| `api_version` | integer | API version number |
| `dashcam_state` | string | Dashcam status |
| `tpms_pressure_fl` | float | Front left tire pressure (bar) |
| `tpms_pressure_fr` | float | Front right tire pressure (bar) |
| `tpms_pressure_rl` | float | Rear left tire pressure (bar) |
| `tpms_pressure_rr` | float | Rear right tire pressure (bar) |

## Important Notes

### Authentication
- Tesla uses OAuth2 for authentication
- Tokens expire and need to be refreshed
- The `teslapy` library handles token management automatically

### Rate Limiting
- Tesla rate limits API requests
- Recommended delay between requests: 10+ seconds
- Excessive requests may result in temporary blocking

### Vehicle States
- **online**: Vehicle is awake and responding
- **asleep**: Vehicle is in sleep mode (parked)
- **offline**: Vehicle is not reachable

### Wake Up Behavior
- When asleep, most API calls will fail
- Use `sync_wake_up()` to wake the vehicle
- Wake up can take 10-30 seconds
- Avoid excessive wake-ups to preserve battery

### GPS Data
- Location data requires the `location_data` endpoint
- GPS coordinates may be null if vehicle just woke up
- Native location fields provide raw GPS data

## TeslaOnTarget Usage

TeslaOnTarget uses the following fields to generate CoT packets:

1. **Position**: `latitude`, `longitude` from `drive_state`
2. **Movement**: `speed`, `heading` from `drive_state`
3. **Status**: `battery_level`, `charging_state` from `charge_state`
4. **Identity**: `vehicle_name` from `vehicle_state`

The system queries these endpoints every 10 seconds:
```python
vehicle.get_vehicle_data(endpoints='location_data;drive_state;charge_state;vehicle_state')
```

This minimizes API calls while getting all necessary data for TAK integration.