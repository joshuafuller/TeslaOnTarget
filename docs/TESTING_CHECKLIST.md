# TeslaOnTarget Testing Checklist

## Docker Installation Test

### Prerequisites
- [ ] Docker installed and running
- [ ] Git installed
- [ ] TAK server accessible
- [ ] Tesla account credentials ready

### Step 1: Clone and Setup
```bash
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget
cp .env.example .env
```
- [ ] Repository cloned successfully
- [ ] .env file created

### Step 2: Configure
Edit `.env` file:
- [ ] Set TAK_SERVER to your TAK server IP
- [ ] Set TESLA_USERNAME to your Tesla email
- [ ] Other settings reviewed

### Step 3: Build Docker Image
```bash
./docker-run.sh build
```
- [ ] Build completes without errors
- [ ] Image `teslaontarget:latest` created

### Step 4: Tesla Authentication
```bash
./docker-run.sh auth
```
- [ ] Browser opens to Tesla login
- [ ] After login, "Page Not Found" error appears
- [ ] URL copied and pasted back
- [ ] "Authentication successful" message appears
- [ ] Vehicle(s) listed

### Step 5: Start Service
```bash
./docker-run.sh start
```
- [ ] Container starts without errors
- [ ] "Started! View logs with: ./docker-run.sh logs" message

### Step 6: Verify Operation
```bash
./docker-run.sh logs
```
- [ ] Logs show successful TAK connection
- [ ] Vehicle data being sent to TAK
- [ ] No error messages

### Step 7: Check TAK Client
- [ ] Open iTAK/ATAK/WebTAK
- [ ] Vehicle appears on map
- [ ] Vehicle details show battery %, location, etc.
- [ ] Updates every 10 seconds when parked
- [ ] Updates every 1 second when driving (dead reckoning)

### Step 8: Management Commands
```bash
./docker-run.sh status
```
- [ ] Shows container running

```bash
./docker-run.sh restart
```
- [ ] Container restarts successfully

```bash
./docker-run.sh stop
```
- [ ] Container stops cleanly

## Traditional Installation Test

### Step 1: Setup
```bash
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget
pip3 install -r requirements.txt
```
- [ ] Dependencies install successfully

### Step 2: Configure
```bash
cp config.py.template config.py
# Edit config.py with TAK server and Tesla email
```
- [ ] Config file created and edited

### Step 3: Authenticate
```bash
python3 -m teslaontarget.auth
```
- [ ] Authentication flow completes

### Step 4: Run
```bash
./teslaontarget.sh start
```
- [ ] Service starts in background

```bash
./teslaontarget.sh logs
```
- [ ] Logs show normal operation

```bash
./teslaontarget.sh status
```
- [ ] Shows running with PID

```bash
./teslaontarget.sh stop
```
- [ ] Service stops cleanly

## Common Issues to Test

### Network Issues
- [ ] Test with TAK server unreachable - should reconnect
- [ ] Test with internet down - should use cached position

### Vehicle States
- [ ] Test with vehicle asleep - should use last position
- [ ] Test with vehicle in garage (no GPS) - should handle gracefully
- [ ] Test while driving - dead reckoning should work

### Edge Cases
- [ ] Multiple vehicles on account - all should appear
- [ ] Long running (24+ hours) - should remain stable
- [ ] Docker restart - should resume automatically