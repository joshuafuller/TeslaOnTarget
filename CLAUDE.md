# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Common Development Commands

### Installation and Setup
```bash
# Install dependencies
pip install -r requirements.txt

# Install package in development mode
pip install -e .

# Create configuration from template
cp config.py.template config.py
```

### Running the Application
```bash
# Using the control script (traditional installation)
./teslaontarget.sh start    # Start in background
./teslaontarget.sh stop     # Stop the service
./teslaontarget.sh restart  # Restart the service
./teslaontarget.sh status   # Check status
./teslaontarget.sh logs     # View live logs

# Direct Python execution
python -m teslaontarget     # Run directly
python -m teslaontarget.auth  # Tesla authentication

# Docker commands
./docker-run.sh build       # Build Docker image
./docker-run.sh auth        # Authenticate with Tesla
./docker-run.sh start       # Start container
./docker-run.sh stop        # Stop container
./docker-run.sh logs        # View logs
./docker-run.sh status      # Check status
```

### Testing
```bash
# Run tests (when implemented)
python -m pytest tests/

# Test configuration
./docker-run.sh test        # Docker test mode
```

### Development Tools
```bash
# Analyze captured Tesla API data (requires DEBUG_MODE=True)
python tools/replay_captures.py         # Quick replay
python tools/analyze_full_captures.py   # Full analysis
python tools/analyze_tesla_api.py       # API response analysis
```

## High-Level Architecture

### Core Components

1. **tesla_api.py** - Tesla API Integration
   - Uses TeslaPy library for OAuth2 authentication
   - Manages vehicle wake/sleep states
   - Polls vehicle data every 10 seconds (configurable)
   - Implements smart wake management to preserve battery

2. **cot.py** - Cursor on Target Message Generation
   - Converts Tesla vehicle data to TAK-compatible CoT XML
   - Generates proper CoT event types (a-f-G-E-V-C for civilian vehicle)
   - Includes vehicle telemetry in CoT remarks field
   - Handles dead reckoning interpolation between updates

3. **tak_client.py** - TAK Server Connection
   - Manages TCP connection to TAK server (plaintext only in v1.0)
   - Implements automatic reconnection on failure
   - Sends formatted CoT messages

4. **config_handler.py** - Configuration Management
   - Loads settings from config.py or environment variables
   - Validates required configuration
   - Supports both Docker and traditional deployments

5. **auth.py** - Tesla Authentication Module
   - Interactive OAuth2 flow with Tesla
   - Token storage and refresh via TeslaPy
   - Browser-based authentication

### Data Flow

1. **Startup Phase**
   - Load configuration
   - Authenticate with Tesla (using cached tokens if available)
   - Connect to TAK server
   - Wake vehicle once to establish initial connection

2. **Main Loop**
   - Poll Tesla API every 10 seconds for vehicle data
   - Convert vehicle data to CoT format
   - Send CoT packet to TAK server
   - If dead reckoning enabled, interpolate position at 1Hz between polls
   - Cache last known position for when vehicle sleeps

3. **Error Handling**
   - Automatic reconnection to TAK server on network failure
   - Graceful handling of sleeping vehicles (uses cached position)
   - Comprehensive logging for troubleshooting

### Key Design Decisions

- **Battery Preservation**: Vehicle is woken only once on startup, then allowed to sleep naturally
- **Position Caching**: Last known position is cached to disk per vehicle (last_position_VIN.json)
- **Dead Reckoning**: Smooth 1Hz updates interpolated between 10-second API polls for better tracking
- **Plaintext Only**: v1.0 uses TCP without SSL/TLS - must run on secure network
- **Multi-Vehicle Support**: Single instance can track multiple vehicles concurrently
  - Each vehicle runs in its own thread
  - Shared TAK connection for efficiency
  - Per-vehicle position caching
  - Optional vehicle filtering via VEHICLE_FILTER config