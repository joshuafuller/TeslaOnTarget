# Changelog

All notable changes to TeslaOnTarget will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [1.2.0](https://github.com/joshuafuller/TeslaOnTarget/compare/v1.1.0...v1.2.0) (2026-06-26)


### Features

* Add Dependabot and security policy ([2658eb2](https://github.com/joshuafuller/TeslaOnTarget/commit/2658eb286d890abf1b7097d692e1dbb690e20c4b))
* Add multi-vehicle support with filtering and concurrent tracking ([d5bc690](https://github.com/joshuafuller/TeslaOnTarget/commit/d5bc6902a537bc387324d3169d23f0fedd203c3f))
* **health:** add TAK health monitor, telemetry, defaults, and entrypoint wiring ([7235c2a](https://github.com/joshuafuller/TeslaOnTarget/commit/7235c2a6fcd5275e840eacc52e1a40159139b7c7))
* **health:** add TAK health monitor, telemetry, defaults, and entrypoint wiring ([6350f81](https://github.com/joshuafuller/TeslaOnTarget/commit/6350f81ac5b0930bff25e2ef29170300b43c5134))
* Implement Docker best practices with multi-stage builds ([6589f98](https://github.com/joshuafuller/TeslaOnTarget/commit/6589f981cf9487f1af349bd24b6956dd71243be4))
* Implement Docker best practices with multi-stage builds ([aef0799](https://github.com/joshuafuller/TeslaOnTarget/commit/aef0799d0be5c5189aea69d9c8fd3d1f1795385e)), closes [#8](https://github.com/joshuafuller/TeslaOnTarget/issues/8)
* Merge pull request [#9](https://github.com/joshuafuller/TeslaOnTarget/issues/9) from joshuafuller/feature/docker-best-practices ([6589f98](https://github.com/joshuafuller/TeslaOnTarget/commit/6589f981cf9487f1af349bd24b6956dd71243be4))
* push-alert on TAK send-stall and critical restart (closes silent-failure gap) ([73a3b2b](https://github.com/joshuafuller/TeslaOnTarget/commit/73a3b2be6f089269e75af0ece31f21980249179a))


### Bug Fixes

* **ci:** extract _stop_health so coverage is 100% on py3.14 ([5d4ba55](https://github.com/joshuafuller/TeslaOnTarget/commit/5d4ba559901466db9b5eb97e0a5def1b795c1717))
* Handle non-writable log volumes gracefully ([a9c22e7](https://github.com/joshuafuller/TeslaOnTarget/commit/a9c22e7dd4746ebcdf3775b934f36ac1a4d460b4))
* Merge pull request [#2](https://github.com/joshuafuller/TeslaOnTarget/issues/2) from joshuafuller/dependabot/github_actions/actions/setup-python-5 ([1e5bc70](https://github.com/joshuafuller/TeslaOnTarget/commit/1e5bc706894452f98d86a8e570a73aabeb133a7f))
* Merge pull request [#3](https://github.com/joshuafuller/TeslaOnTarget/issues/3) from joshuafuller/dependabot/github_actions/softprops/action-gh-release-2 ([ac04f6d](https://github.com/joshuafuller/TeslaOnTarget/commit/ac04f6d6f855d82ae01066096a363d5796cd5687))
* Merge pull request [#4](https://github.com/joshuafuller/TeslaOnTarget/issues/4) from joshuafuller/dependabot/github_actions/actions/checkout-4 ([022995b](https://github.com/joshuafuller/TeslaOnTarget/commit/022995b8dec24356fa63f2fc2e2a0ab3f91b2421))
* Merge pull request [#5](https://github.com/joshuafuller/TeslaOnTarget/issues/5) from joshuafuller/dependabot/github_actions/docker/build-push-action-6 ([dee1031](https://github.com/joshuafuller/TeslaOnTarget/commit/dee1031fad179aabce16c348d26a380b48f9c251))
* Merge pull request [#6](https://github.com/joshuafuller/TeslaOnTarget/issues/6) from joshuafuller/dependabot/docker/python-3.13-slim ([9d10db5](https://github.com/joshuafuller/TeslaOnTarget/commit/9d10db57c5c97ad14b87150542d04276828b8cad))
* Merge pull request [#7](https://github.com/joshuafuller/TeslaOnTarget/issues/7) from joshuafuller/fix/update-pypi-publish-action ([7961a86](https://github.com/joshuafuller/TeslaOnTarget/commit/7961a862a2cbc681578f997543ad0ff56988002e))
* Remove PyPI deployment from CI/CD workflow ([eab7fc1](https://github.com/joshuafuller/TeslaOnTarget/commit/eab7fc1a582645b89f5c5296ac8f5f8a89b11b52))
* restore Tesla Owner API by pinning teslapy&gt;=2.9.2 (TLS 1.3) ([#25](https://github.com/joshuafuller/TeslaOnTarget/issues/25)) ([73f66ad](https://github.com/joshuafuller/TeslaOnTarget/commit/73f66ada6d4e8b04288e77c79ab28f26ceddcc7c))
* **review:** address Copilot findings on [#36](https://github.com/joshuafuller/TeslaOnTarget/issues/36) ([bc4af34](https://github.com/joshuafuller/TeslaOnTarget/commit/bc4af34ea3b98454bd5764d3054ea2aeb30c97a8))
* **review:** dead_reckoning_update treats 0.0 as a valid coordinate ([5c4968b](https://github.com/joshuafuller/TeslaOnTarget/commit/5c4968bfa2f7d51d5ce3133281ea74a300cf2491))
* **review:** md5 usedforsecurity=False to avoid FIPS crash ([#33](https://github.com/joshuafuller/TeslaOnTarget/issues/33)) ([0b6110d](https://github.com/joshuafuller/TeslaOnTarget/commit/0b6110d19a8c498b374200ff0b5d22d418dc48ef))
* **review:** remediate Copilot findings on [#32](https://github.com/joshuafuller/TeslaOnTarget/issues/32) ([134ade6](https://github.com/joshuafuller/TeslaOnTarget/commit/134ade6cf6bbb3f43b512fd255d7b477c6ca94a0))
* **review:** robust VEHICLE_FILTER coercion + correct MagicMock __getitem__ ([#34](https://github.com/joshuafuller/TeslaOnTarget/issues/34)) ([fc9f5a3](https://github.com/joshuafuller/TeslaOnTarget/commit/fc9f5a3144027279d0acf44c053fd91d136e3157))
* robustness + observability — alerting, fail-fast send_cot, dead-state, CI gates ([9b02981](https://github.com/joshuafuller/TeslaOnTarget/commit/9b029813ed072486465607da10f052000afc2675))
* send_cot fails fast instead of blocking forever; drop dead state ([b1ef90a](https://github.com/joshuafuller/TeslaOnTarget/commit/b1ef90a4fd2ee684102818a8df9ab5971a138ab2))
* Update pypa/gh-action-pypi-publish to supported version ([7961a86](https://github.com/joshuafuller/TeslaOnTarget/commit/7961a862a2cbc681578f997543ad0ff56988002e))
* Update pypa/gh-action-pypi-publish to supported version ([6f88ccf](https://github.com/joshuafuller/TeslaOnTarget/commit/6f88ccfb9ed7778b12fb2ccfffbe636027df1a98))
* Update release workflow to use newer action ([f5583f7](https://github.com/joshuafuller/TeslaOnTarget/commit/f5583f744de1fb14563df3d681325eb26b4f7391))
* updating DeepWiki badge ([cf82ba8](https://github.com/joshuafuller/TeslaOnTarget/commit/cf82ba8d3071e88de4d3260fbdb1ed9aa06aa175))

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
