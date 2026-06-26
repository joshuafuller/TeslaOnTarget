# Troubleshooting

## Vehicle not appearing in TAK

1. Check connectivity to the TAK server: `telnet your-tak-server 8085`.
2. Verify the vehicle is online in the Tesla app.
3. Check logs: `./teslaontarget.sh logs` (or `./docker-run.sh logs`) — look for `Successfully sent CoT packet`.
4. Confirm your TAK client is connected to the same server.
5. If the app logs successful sends but you don't see it: refresh the TAK client (a stale client clock can hide markers whose `stale` time has passed).

## Authentication issues

**Source install** — clear the cached token and re-authenticate:

```bash
rm cache.json
python3 -m teslaontarget.auth
```

**Docker** — the token lives in the `tesla_data` volume; re-run the auth container:

```bash
docker run -it --env-file .env -v tesla_data:/data ghcr.io/joshuafuller/teslaontarget auth
```

See [AUTHENTICATION.md](AUTHENTICATION.md) for the full login walkthrough.

## Vehicle shows the wrong location

- The vehicle may be in a parking garage with no GPS.
- Wait ~10s for the next update.

## High Tesla battery drain

- Normal: the vehicle is woken only once, on startup.
- Abnormal: check logs for repeated wake attempts, then restart the service.

## Connection keeps dropping

The client fails fast and reconnects in the background. Persistent drops usually mean the TAK server is unreachable or restarting — verify the server and the network path. The health monitor will force reconnects and, after a prolonged stall, exit for a supervisor restart (set `ALERT_WEBHOOK_URL` to be paged when this happens — see [CONFIGURATION.md](CONFIGURATION.md)).
