# TeslaOnTarget Roadmap

## Version 1.0 (Current)
- ✅ Basic Tesla to TAK integration
- ✅ Plaintext TCP connection to TAK servers
- ✅ Dead reckoning for smooth tracking
- ✅ Docker support
- ✅ Multi-vehicle support (run multiple instances)
- ✅ Smart wake management

## Version 2.0 (Planned)
- 🔐 **SSL/TLS Support** for secure TAK connections
  - Certificate-based authentication
  - Support for TAK Server SSL ports
  - Mutual TLS authentication
- 🔐 **QUIC Protocol Support**
  - Modern, efficient transport
  - Better performance over lossy networks
- 📱 Multi-vehicle support in single instance
- 🔧 Web configuration interface
- 📊 Prometheus metrics endpoint

## Version 3.0 (Future)
- 🌐 TAK Server authentication integration
- 📲 Mobile app for configuration
- 🚗 Additional vehicle telemetry
  - Tire pressure
  - Door/trunk status
  - Climate control state
- 🗺️ Route planning integration
- 📈 Historical tracking database

## Security Roadmap
1. **Phase 1** (v1.0): Local network deployment only
2. **Phase 2** (v2.0): SSL/TLS for secure remote connections
3. **Phase 3** (v3.0): Full TAK authentication integration

## Contributing
If you'd like to help implement any of these features, please see [CONTRIBUTING.md](../CONTRIBUTING.md).