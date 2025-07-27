# Docker Guide for TeslaOnTarget

This guide covers everything you need to run TeslaOnTarget in Docker.

**Security Note**: TeslaOnTarget v1.0 only supports plaintext TCP connections. Run it on the same network as your TAK server, ideally on the same machine. Do not expose across WAN connections.

## Docker Images

### Pre-built Images
Pre-built images are available from GitHub Container Registry:
```bash
docker pull ghcr.io/joshuafuller/teslaontarget:latest
```

Available tags:
- `latest` - Latest stable release (from main branch)
- `main` - Latest development build (auto-built on push)
- `v1.0.0`, `v1.0`, `v1` - Specific version tags
- `pr-123` - Pull request builds (for testing)

### Multi-Architecture Support
Images are automatically built for:
- `linux/amd64` (Intel/AMD x86_64)
- `linux/arm64` (ARM64, including Apple Silicon)

## Quick Start

### 1. Clone the Repository
```bash
git clone https://github.com/joshuafuller/TeslaOnTarget.git
cd TeslaOnTarget
```

### 2. Configure Environment
```bash
cp .env.example .env
# Edit .env with your TAK server IP and Tesla email
```

### 3. Build and Run
```bash
# Build the Docker image
./docker-run.sh build

# Authenticate with Tesla (one-time setup)
./docker-run.sh auth
# Follow the prompts:
# 1. Browser will open to Tesla login
# 2. After login, you'll see "Page Not Found" - this is normal
# 3. Copy the ENTIRE URL from your browser
# 4. Paste it back in the terminal

# Start tracking
./docker-run.sh start

# View logs
./docker-run.sh logs
```

## 📦 Docker Compose (Recommended)

### 1. Setup Configuration
```bash
# Copy the example configuration
cp .env.example .env

# Edit with your settings
nano .env
```

### 2. Authenticate with Tesla
```bash
docker-compose --profile auth run --rm tesla-auth
```

### 3. Start the Service
```bash
docker-compose up -d
```

### 4. View Logs
```bash
docker-compose logs -f
```

### 5. Stop the Service
```bash
docker-compose down
```

## 🔧 Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `TAK_SERVER` | TAK server IP address | - | Yes |
| `TESLA_USERNAME` | Tesla account email | - | Yes |
| `TAK_PORT` | TAK server port | `8085` | ❌ |
| `API_LOOP_DELAY` | Seconds between API calls | `10` | ❌ |
| `DEAD_RECKONING_ENABLED` | Enable position interpolation | `True` | ❌ |
| `DEAD_RECKONING_DELAY` | Seconds between interpolations | `1` | ❌ |
| `DEBUG_MODE` | Save API responses for debugging | `False` | ❌ |

## Volume Mounts

| Volume Path | Purpose |
|-------------|---------|
| `/data` | Persistent storage for Tesla auth tokens and last position |
| `/logs` | Application logs |

## Common Docker Commands

### Build Image
```bash
docker build -t teslaontarget .
```

### Test Configuration
```bash
docker run --rm \
  -e TAK_SERVER=192.168.1.100 \
  -e TESLA_USERNAME=your@email.com \
  teslaontarget test
```

### View Logs
```bash
docker logs -f teslaontarget
```

### Re-authenticate
```bash
# Remove old auth
docker run --rm -v tesla_data:/data alpine rm -f /data/cache.json

# Run auth again
docker run -it \
  -e TESLA_USERNAME=your@email.com \
  -v tesla_data:/data \
  teslaontarget auth
```

### Shell Access (Debug)
```bash
docker run -it --rm \
  -v tesla_data:/data \
  -v tesla_logs:/logs \
  teslaontarget shell
```

## Updating

### Pull Latest Changes
```bash
git pull
docker-compose build
docker-compose up -d
```

### Or Rebuild Fresh
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

## Troubleshooting

### Container Won't Start
Check logs:
```bash
docker logs teslaontarget
```

Common issues:
- Missing TAK_SERVER or TESLA_USERNAME environment variables
- Not authenticated with Tesla (run auth command first)
- TAK server not reachable from container

### Authentication Issues
```bash
# Check if authenticated
docker run --rm -v tesla_data:/data alpine ls -la /data/

# Re-authenticate
docker run --rm -v tesla_data:/data alpine rm -f /data/cache.json
docker-compose --profile auth run --rm tesla-auth
```

### Network Issues
Test TAK server connectivity:
```bash
docker run --rm --network container:teslaontarget alpine nc -zv YOUR_TAK_SERVER 8085
```

### Permission Issues
Fix volume permissions:
```bash
docker run --rm -v tesla_data:/data alpine chown -R 1000:1000 /data
docker run --rm -v tesla_logs:/logs alpine chown -R 1000:1000 /logs
```

## 🏗️ Building for Different Architectures

### Multi-arch Build (AMD64 + ARM64)
```bash
docker buildx create --use
docker buildx build --platform linux/amd64,linux/arm64 -t teslaontarget:latest .
```

## Security Best Practices

1. **Local Network Only**: v1.0 uses plaintext TCP - run on same network as TAK server
2. **Use Secrets**: For production, use Docker secrets instead of environment variables
3. **Network Isolation**: Put TAK server and TeslaOnTarget on same Docker network
4. **Read-only Root**: Add `read_only: true` to docker-compose.yml
5. **Non-root User**: Container runs as non-root user by default
6. **No WAN Exposure**: Do not expose TAK ports across Internet without VPN

## Monitoring

### Health Check
Add to docker-compose.yml:
```yaml
healthcheck:
  test: ["CMD", "pgrep", "-f", "teslaontarget"]
  interval: 30s
  timeout: 10s
  retries: 3
```

### Prometheus Metrics
Mount additional volume for metrics:
```yaml
volumes:
  - tesla_metrics:/metrics
```

## Example Deployments

### Home Network
```bash
docker run -d \
  -e TAK_SERVER=192.168.1.100 \
  -e TESLA_USERNAME=john@example.com \
  -v tesla_data:/data \
  -v tesla_logs:/logs \
  --name teslaontarget \
  --restart unless-stopped \
  teslaontarget
```

### Cloud Deployment (with VPN)
```yaml
services:
  teslaontarget:
    image: teslaontarget:latest
    environment:
      - TAK_SERVER=10.8.0.1  # VPN IP
      - TESLA_USERNAME=${TESLA_USERNAME}
    volumes:
      - tesla_data:/data
      - tesla_logs:/logs
    depends_on:
      - vpn
    network_mode: service:vpn
```

### Kubernetes
See `kubernetes/` directory for Helm charts and manifests.

## 📝 Notes

- Authentication tokens are stored in the `tesla_data` volume
- Logs are rotated automatically (10MB max, 3 files)
- Container supports both x86_64 and ARM64 architectures
- Dead reckoning runs at 1Hz by default for smooth tracking