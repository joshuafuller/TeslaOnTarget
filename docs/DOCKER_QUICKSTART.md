# Docker Quick Start for TeslaOnTarget

## Current Status
Your TeslaOnTarget is now running successfully in Docker!

- **Vehicle**: [Your Vehicle Name] (Model Y Performance)
- **TAK Server**: Connected to [YOUR_TAK_SERVER]:8085
- **Update Rate**: Every 10 seconds
- **Dead Reckoning**: Enabled (1Hz interpolation)
- **Debug Mode**: Enabled (capturing API responses)

## Key Information from Logs
- Battery: 80%
- Location: [REDACTED]
- Status: Parked (Gear: P)
- Range: 221 miles
- Sentry Mode: ON
- Doors: Locked
- UID: TESLA-[UNIQUE_ID]

## Quick Commands

### View Live Logs
```bash
./docker-run.sh logs
```

### Check Status
```bash
./docker-run.sh status
```

### Stop Tracking
```bash
./docker-run.sh stop
```

### Restart
```bash
./docker-run.sh restart
```

### View Captured API Data
```bash
# List captures
docker run --rm -v tesla_data:/data alpine ls -la /data/tesla_api_captures/

# View a specific capture
docker run --rm -v tesla_data:/data alpine cat /data/tesla_api_captures/[filename]
```

## Verify in TAK

1. Open your TAK client (iTAK, ATAK, or WebTAK)
2. Look for your vehicle on the map
3. You should see:
   - Tesla icon (vehicle type: a-f-G-E-V-C)
   - Battery level: 80%
   - Detailed remarks with vehicle info

## Data Locations

All data is stored in Docker volumes:
- **tesla_data**: Authentication tokens, position cache, API captures
- **tesla_logs**: Application logs

## Test Drive Checklist

When you take the car for a drive:
1. Dead reckoning should activate automatically when in D or R
2. You'll see 1Hz position updates between the 10-second API polls
4. Speed will be shown in the CoT track element

## Troubleshooting

### If vehicle stops updating:
```bash
# Check logs for errors
./docker-run.sh logs | grep ERROR

# Restart the service
./docker-run.sh restart
```

### To disable debug captures:
Edit `.env` and set:
```
DEBUG_MODE=False
```
Then restart:
```bash
./docker-run.sh restart
```

## Next Steps

1. **Monitor Performance**: Watch for any rate limiting warnings
2. **Test Dead Reckoning**: Take a drive and verify smooth 1Hz updates
4. **Production Mode**: Once tested, disable DEBUG_MODE to save space

---
Your Tesla is now successfully feeding position data to your TAK server!