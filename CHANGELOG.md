# Changelog

All notable changes to TeslaOnTarget will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.0.0] - 2025-07-27

### Added
- Initial release of TeslaOnTarget
- Real-time Tesla vehicle tracking to TAK servers
- Docker support with easy authentication flow
- Dead reckoning for smooth 1Hz position updates
- Comprehensive vehicle telemetry (battery, charging, climate, security)
- Smart wake management to preserve vehicle battery
- Multi-TAK compatibility (iTAK, ATAK, WebTAK)
- Rate limiting protection for Tesla API
- Persistent position caching
- Debug mode for API response capture
- Comprehensive logging system
- Control script for easy management (teslaontarget.sh)
- Docker Compose orchestration
- Environment variable configuration

### Fixed
- Double speed display issue (mph to m/s conversion)
- Vehicle type compatibility for WebTAK (a-f-G-E-V-C)
- Dead reckoning to interpolate between API updates
- Docker symlink issues for log files

### Known Issues
- Autopilot state field not available in current Tesla API responses
- SSL/TLS connections to TAK servers not yet supported (plaintext TCP only)
- Must run on same network as TAK server for security

### Security
- Secure OAuth2 token management via TeslaPy
- All sensitive files excluded from version control
- Docker secrets management for credentials