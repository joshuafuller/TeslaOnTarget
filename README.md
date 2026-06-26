# TeslaOnTarget

Bridge your Tesla vehicle with TAK (Team Awareness Kit) servers for real-time position tracking.

![Python](https://img.shields.io/badge/python-3.11+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![TAK](https://img.shields.io/badge/TAK-Compatible-orange.svg)
[![CI](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/ci-cd.yml/badge.svg)](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/ci-cd.yml)
[![Security](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/security.yml/badge.svg)](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/security.yml)
[![Release](https://img.shields.io/github/v/release/joshuafuller/TeslaOnTarget)](https://github.com/joshuafuller/TeslaOnTarget/releases)
![GHCR](https://img.shields.io/badge/ghcr.io-ready-brightgreen)
[![Ask DeepWiki](https://deepwiki.com/badge.svg)](https://deepwiki.com/joshuafuller/TeslaOnTarget)

TeslaOnTarget connects your Tesla to a TAK server and streams live position and status as Cursor-on-Target (CoT) messages — for emergency response, fleet or personal tracking, or testing TAK systems with real vehicle data.

## How it works

```mermaid
flowchart LR
    tesla["Tesla Owner API"]
    subgraph app["TeslaOnTarget container"]
        cli["cli<br/>per-vehicle threads"]
        api["tesla_api<br/>poll + dead reckoning"]
        mapper["vehicle_mapper<br/>payload to CoT dict"]
        cot["cot<br/>build CoT XML"]
        takc["tak_client<br/>TCP send"]
        health["health<br/>monitor + alerts"]
        cli --> api --> mapper --> cot --> takc
        health -.->|watches| takc
    end
    tesla -->|vehicle data every 10s| cli
    takc -->|CoT over TCP| takserver["TAK Server"]
    takserver --> clients["ATAK / iTAK / WebTAK"]
    health -.->|webhook/ntfy on stall| alert["Alert endpoint"]
```

Poll Tesla → map the payload to a CoT event → send it to your TAK server, with 1 Hz dead-reckoning between polls and a health monitor that reconnects (and alerts) on failure. Full detail: **[docs/ARCHITECTURE.md](docs/ARCHITECTURE.md)**.

## Features

- **Real-time tracking** — GPS updates every 10s with 1Hz dead-reckoning in between
- **Rich status** — battery, charging, and parked-security (doors/windows/sentry) in the CoT remarks
- **Multi-vehicle** — track your whole account from one instance (iTAK / ATAK / WebTAK)
- **Self-healing** — health monitor reconnects on stalled sends and restarts for recovery
- **Failure alerting** — optional webhook/ntfy push when sends stall (opt-in)
- **Battery-friendly** — wakes the vehicle once, reports last position while it sleeps

## Quick start (Docker)

```bash
docker pull ghcr.io/joshuafuller/teslaontarget:latest   # or :1.2.0 to pin a release

cp .env.example .env          # set TAK_SERVER and TESLA_USERNAME

# one-time Tesla login
docker run -it --env-file .env -v tesla_data:/data ghcr.io/joshuafuller/teslaontarget auth

# start tracking
docker run -d --env-file .env -v tesla_data:/data -v tesla_logs:/logs \
  --name teslaontarget --restart unless-stopped ghcr.io/joshuafuller/teslaontarget
```

Prefer a non-Docker install? `uv sync`, copy `config.py.template` → `config.py`, run `uv run python -m teslaontarget.auth`, then `./teslaontarget.sh start`. Full guides below.

## Requirements

- **Python 3.11+** (bundled in the Docker image)
- A **Tesla account** with a vehicle
- A **CoT-capable TAK server** reachable over plaintext TCP

## ⚠️ Security

Only **plaintext TCP** to the TAK server is supported (no TLS yet). Keep TeslaOnTarget on the same LAN as your TAK server (ideally on the TAK host) or behind a VPN — do not expose it across the internet.

## Configuration

Set via environment variables (Docker) or `config.py` (source). The essentials:

| Setting | Description | Default |
|---------|-------------|---------|
| `TAK_SERVER` (+ `TAK_PORT`) | TAK server host/IP and port — **Docker** | required |
| `COT_URL` | Full `tcp://host:port` — **source** `config.py` | required |
| `TESLA_USERNAME` | Tesla account email | required |
| `ALERT_WEBHOOK_URL` | ntfy topic / webhook for failure alerts | _(off)_ |

Full reference (all options, multi-vehicle filtering, debug capture, what's transmitted): **[docs/CONFIGURATION.md](docs/CONFIGURATION.md)**.

## Documentation

- **[Documentation index](docs/README.md)** — start here
- [Architecture](docs/ARCHITECTURE.md) · [Docker guide](docs/DOCKER.md) · [Tesla authentication](docs/AUTHENTICATION.md) · [Configuration & operations](docs/CONFIGURATION.md) · [Troubleshooting](docs/TROUBLESHOOTING.md)
- [CHANGELOG](CHANGELOG.md) · [Releases](https://github.com/joshuafuller/TeslaOnTarget/releases) · [Roadmap](docs/ROADMAP.md) · [Contributing](CONTRIBUTING.md)

## Known limitations

- No SSL/TLS — plaintext TCP only (planned; see the roadmap)
- Wakes the vehicle once on startup only (by design, to preserve battery)
- No authentication to the TAK server — relies on network security

## License

MIT — see [LICENSE](LICENSE). Not affiliated with Tesla, Inc. Use responsibly: mind Tesla API rate limits, battery consumption, and local laws on vehicle tracking.

---

Made with ❤️ for the TAK community
