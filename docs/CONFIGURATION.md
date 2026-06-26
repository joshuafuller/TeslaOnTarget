# Configuration & Operations

Settings can be provided as **environment variables** (Docker, via `.env`) or in a **`config.py`** file (source installs — `cp config.py.template config.py`).

## Configuration options

| Setting | Description | Default |
|---------|-------------|---------|
| `COT_URL` | TAK server URL (`tcp://host:port`) | `tcp://YOUR_TAK_SERVER:8085` |
| `TESLA_USERNAME` | Your Tesla account email | required |
| `API_LOOP_DELAY` | Seconds between Tesla API calls | `10` |
| `LAST_POSITION_FILE` | Cache file for position data | `last_known_position.json` |
| `DEBUG_MODE` | Save all Tesla API responses for analysis | `False` |
| `DEAD_RECKONING_ENABLED` | Interpolate position between API updates | `True` (Docker default) |
| `DEAD_RECKONING_DELAY` | Seconds between interpolated updates (1 = 1Hz) | `1` |
| `ALERT_WEBHOOK_URL` | ntfy topic / webhook for failure alerts (empty = disabled) | _(empty)_ |
| `HEALTH_NO_SEND_SECONDS` | Stall threshold before forcing a reconnect (0 = auto) | `0` |
| `HEALTH_CHECK_INTERVAL` | Seconds between health checks (0 = auto) | `0` |
| `HEALTH_HARD_RESTART_SECONDS` | No-send threshold before exiting for a supervisor restart (0 = auto) | `0` |
| `HEALTH_FILE` | Path to the health snapshot file | `health.json` |

In Docker, `TAK_SERVER` + `TAK_PORT` are combined into `COT_URL` by the entrypoint.

## Failure alerting

Set `ALERT_WEBHOOK_URL` to an [ntfy](https://ntfy.sh) topic or any webhook to be paged when the health monitor detects a prolonged send stall or triggers a recovery restart. Empty (the default) disables alerting.

## TAK server setup

- Configure a **TCP input** on your chosen port (default `8085`).
- Plaintext only — keep TAK traffic on the local network.
- TAK clients must share the network with (or have routing to) the server.

## Management commands (source install)

```bash
./teslaontarget.sh start     # start tracking in background
./teslaontarget.sh stop      # stop
./teslaontarget.sh restart   # restart
./teslaontarget.sh status    # check if running
./teslaontarget.sh logs      # live logs
python3 -m teslaontarget.auth  # set up / refresh Tesla auth
```

For Docker, use `./docker-run.sh {build,auth,start,logs,status}` or `docker compose`.

## Verifying it works

1. Logs show `Connected to TAK server` and `Successfully sent CoT packet`.
2. Your vehicle appears on the map in iTAK/ATAK/WebTAK and updates every ~10s.

## Multi-vehicle support

By default all vehicles on the account are tracked. Filter with `VEHICLE_FILTER`:

```python
VEHICLE_FILTER = []                                   # all (default)
VEHICLE_FILTER = ["Model Y", "Cybertruck"]            # by display name
VEHICLE_FILTER = ["5YJ3E1EA8NF000000"]                # by VIN
```

Each vehicle gets its own CoT identifier, its own position cache (`last_position_<VIN>.json`), and its own thread, sharing one TAK connection.

## Data transmitted

Each CoT message includes: GPS position, heading, speed (when moving), battery level, charging state, and the vehicle name as callsign.

## Debug mode & data capture

With `DEBUG_MODE = True`, every Tesla API response is saved to `tesla_api_captures/` for debugging and replay:

```bash
python3 tools/replay_captures.py         # quick view of extracted data
python3 tools/analyze_full_captures.py   # full field analysis across captures
```
