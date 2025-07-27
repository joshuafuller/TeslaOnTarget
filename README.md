
# TeslaOnTarget

Bridge your Tesla vehicle with TAK (Team Awareness Kit) servers for real-time position tracking.

![Python](https://img.shields.io/badge/python-3.7+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![TAK](https://img.shields.io/badge/TAK-Compatible-orange.svg)
![Tesla](https://img.shields.io/badge/Tesla-API-red.svg)
![Docker](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/docker-publish.yml/badge.svg)
![GitHub Container Registry](https://img.shields.io/badge/ghcr.io-ready-brightgreen)

## What is TeslaOnTarget?

TeslaOnTarget is a lightweight Python application that connects your Tesla vehicle to a TAK (Team Awareness Kit) server, enabling real-time vehicle tracking in tactical awareness applications. It bridges the gap between Tesla's modern API and military/emergency response systems that use Cursor on Target (CoT) messaging.

### Use Cases
- **Emergency Response** - Track response vehicles in real-time
- **Fleet Management** - Monitor multiple Tesla vehicles on a single TAK display
- **Personal Tracking** - Keep tabs on your vehicle's location and status
- **Integration Testing** - Test TAK systems with real vehicle data

## Features

- **Real-time Vehicle Tracking** - GPS position updates every 10 seconds
- **Battery & Charging Status** - Monitor charge level and time to completion
- **Smart Wake Management** - Wakes vehicle only once, preserves battery when parked
- **Multi-TAK Compatible** - Tested with iTAK, ATAK, and WebTAK
- **Security Alerts** - Warnings for open windows/doors when parked
- **Dead Reckoning** - Smooth 1Hz position updates between 10-second API polls
- **Resilient Connection** - Automatic reconnection and error recovery
- **Detailed Logging** - Comprehensive logs for troubleshooting
- **Secure Token Storage** - OAuth2 token management via TeslaPy
- **Location Caching** - Continues reporting last position when vehicle sleeps

## Requirements

- **Python 3.7+** 
- **Tesla Account** with a vehicle
- **TAK Server** (one of the following):
  - [OpenTAKServer](https://github.com/brian7704/OpenTAKServer)
  - TAK Server (Official)
  - Any CoT-compatible server
- **Network Access** to both internet (Tesla API) and your TAK server

### ⚠️ Important Security Note
**This version only supports plaintext TCP connections to TAK servers.** SSL/TLS/QUIC support is planned for a future release. For security:
- Run TeslaOnTarget on the same network as your TAK server
- Ideally run it directly on the TAK server machine
- Do NOT expose across WAN/Internet connections
- Use VPN if remote access is required

## Quick Start

### Option 1: Docker (Recommended)

#### Using Pre-built Image (Easiest)
```bash
# Pull the latest image
docker pull ghcr.io/joshuafuller/teslaontarget:latest

# Create configuration
wget https://raw.githubusercontent.com/joshuafuller/TeslaOnTarget/main/.env.example
cp .env.example .env
# Edit .env with your TAK server IP and Tesla email

# Authenticate with Tesla
docker run -it --env-file .env -v tesla_data:/data ghcr.io/joshuafuller/teslaontarget auth

# Run TeslaOnTarget
docker run -d --env-file .env -v tesla_data:/data -v tesla_logs:/logs \
  --name teslaontarget --restart unless-stopped \
  ghcr.io/joshuafuller/teslaontarget
```

#### Building from Source
```bash
# Clone repository
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget

# Setup configuration
cp .env.example .env
# Edit .env with your TAK server IP and Tesla email

# Build Docker image
./docker-run.sh build

# Authenticate with Tesla (one-time)
./docker-run.sh auth

# Start tracking
./docker-run.sh start

# View logs
./docker-run.sh logs
```

See [docs/DOCKER.md](docs/DOCKER.md) for detailed Docker instructions and [docs/AUTHENTICATION.md](docs/AUTHENTICATION.md) for Tesla login help.

### Option 2: Traditional Installation

#### 1. Clone & Install

```bash
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget
pip3 install -r requirements.txt
```

#### 2. Configure

Copy the template and edit with your settings:
```bash
cp config.py.template config.py
nano config.py
```

Required settings:
```python
COT_URL = "tcp://192.168.1.100:8085"  # Your TAK server
TESLA_USERNAME = "your@email.com"      # Your Tesla account email
```

#### 3. Authenticate with Tesla

```bash
python3 -m teslaontarget.auth
```

This will:
1. Open Tesla's login page in your browser
2. After login, you'll land on a "Page Not Found" error (this is normal!)
3. Copy the ENTIRE URL from your browser's address bar
4. Paste it back in the terminal when prompted

#### 4. Start Tracking

```bash
./teslaontarget.sh start
```

View live logs:
```bash
./teslaontarget.sh logs
```

## Configuration Options

| Setting | Description | Default |
|---------|-------------|---------|
| `COT_URL` | TAK server URL (tcp://host:port) | `tcp://YOUR_TAK_SERVER:8085` |
| `API_LOOP_DELAY` | Seconds between Tesla API calls | `10` |
| `TESLA_USERNAME` | Your Tesla account email | Required |
| `LAST_POSITION_FILE` | Cache file for position data | `last_known_position.json` |
| `DEBUG_MODE` | Save all Tesla API responses for analysis | `False` |
| `DEAD_RECKONING_ENABLED` | Interpolate position between API updates for smooth tracking | `True` |
| `DEAD_RECKONING_DELAY` | Seconds between interpolated position updates (1 = 1Hz) | `1` |

## 📡 TAK Server Setup

### FreeTAK Server
Default configuration should work. Ensure TCP port 8085 is open.

### TAK Server
Configure a TCP input on port 8085 (or your chosen port).

### Network Requirements
- Firewall must allow TCP connections to TAK server (plaintext only in v1.0)
- No authentication required (or configure as needed)
- TAK clients must be on same network or have routing to server
- **Security**: Keep TAK traffic on local network only due to plaintext limitation

## Management Commands

Single control script for all operations:

```bash
./teslaontarget.sh start     # Start tracking in background
./teslaontarget.sh stop      # Stop tracking
./teslaontarget.sh restart   # Restart tracking
./teslaontarget.sh status    # Check if running
./teslaontarget.sh logs      # View live logs
./teslaontarget.sh help      # Show all commands
```

For Tesla authentication:
```bash
python3 -m teslaontarget.auth  # Set up or refresh Tesla authentication
```

## Verifying Installation

After starting TeslaOnTarget, verify it's working:

1. **Check logs**: `./docker-run.sh logs` (Docker) or `./teslaontarget.sh logs` (Traditional)
   - Should show "Connected to TAK server"
   - Should show "Successfully sent CoT packet"

2. **Check TAK client**:
   - Open iTAK/ATAK/WebTAK
   - Look for your vehicle on the map
   - Verify updates every 10 seconds

3. **Check status**: `./docker-run.sh status`
   - Should show "TeslaOnTarget is running"

## Troubleshooting

### Vehicle Not Appearing in TAK
1. Check TAK server connectivity: `telnet your-tak-server 8085`
2. Verify vehicle is online in Tesla app
3. Check logs: `./teslaontarget.sh logs`
4. Ensure TAK client is connected to same server

### Authentication Issues
```bash
rm cache.json
python3 -m teslaontarget.auth
```

### Vehicle Shows Wrong Location
- Vehicle may be in parking garage (no GPS)
- Wait 10 seconds for next update
- Check if vehicle is actually at shown location

### High Tesla Battery Drain
- Normal: Vehicle is woken once on startup only
- Abnormal: Check logs for repeated wake attempts
- Solution: Restart the service

## 📁 Project Structure

```
TeslaOnTarget/
├── teslaontarget/        # Main package directory
│   ├── __init__.py      # Package initialization
│   ├── __main__.py      # Entry point
│   ├── tesla_api.py     # Tesla API integration
│   ├── cot.py           # CoT message generation
│   ├── config_handler.py # Configuration management
│   ├── tak_client.py    # TAK server connection
│   ├── utils.py         # Helper functions
│   └── auth.py          # Tesla authentication
├── teslaontarget.sh     # Single control script (start/stop/status)
├── config.py            # Your configuration (don't commit!)
├── requirements.txt     # Python dependencies
├── setup.py             # Package installation
├── docs/                # Detailed documentation
│   ├── README.md        # Full documentation
│   └── tesla_api_reference.md  # Tesla API details
└── tests/               # Unit tests
```

## Security Considerations

- **Never commit** `config.py` or `cache.json` to version control
- **Plaintext Only**: v1.0 uses unencrypted TCP - keep on local network only
- Run TeslaOnTarget on same machine or network as TAK server
- Keep your TAK server behind a firewall or VPN
- Use network segmentation for TAK infrastructure
- Rotate Tesla tokens periodically (automatic via TeslaPy)
- Monitor `teslaontarget.log` for suspicious activity

## Known Limitations

- **No SSL/TLS support** - plaintext TCP only (SSL planned for v2.0)
- Updates only when vehicle is awake or every 10 seconds when asleep (last position)
- Cannot wake vehicle remotely after initial startup (by design)
- Single vehicle per instance (run multiple instances for fleets)
- No authentication to TAK server (depends on network security)

## 📊 Data Transmitted

TeslaOnTarget sends the following in each CoT message:
- GPS Position (latitude/longitude)
- Heading (0-360 degrees)
- Speed (when moving)
- Battery level (percentage)
- Charging state
- Vehicle name as callsign

## Roadmap

See [docs/ROADMAP.md](docs/ROADMAP.md) for planned features, including SSL/TLS support in v2.0.

## Contributing

Contributions are welcome! Please see [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines.

## 📜 License

MIT License - see [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- [TeslaPy](https://github.com/tdorssers/TeslaPy) - Tesla API Python implementation
- Tesla owners community for API documentation

## Disclaimer

This project is not affiliated with Tesla, Inc. Use at your own risk. Be mindful of:
- Tesla API rate limits
- Vehicle battery consumption
- Local laws regarding vehicle tracking

## 🐛 Debug Mode & Data Analysis

When `DEBUG_MODE = True` in your config.py, all Tesla API responses are saved to the `tesla_api_captures/` directory. This is useful for:

- Debugging issues with speed, vehicle state detection, etc.
- Analyzing Tesla API responses
- Replaying drive data for development

### Analyzing Captured Data

Two analysis tools are available:

1. **Quick replay tool** - Shows extracted data:
```bash
python3 tools/replay_captures.py
```

2. **Full analysis tool** - Analyzes complete API responses:
```bash
python3 tools/analyze_full_captures.py
```

The full analysis tool will:
- List ALL available fields in the Tesla API
- Find all vehicle state related fields
- Show fields that change between captures
- Provide detailed state analysis

Perfect for discovering new fields and debugging issues!

## 📞 Support

- **Issues**: [GitHub Issues](https://github.com/yourusername/TeslaOnTarget/issues)
- **Discussions**: [GitHub Discussions](https://github.com/yourusername/TeslaOnTarget/discussions)
- **Documentation**: See [docs/](docs/) directory

---

Made with ❤️ for the TAK community

