# Docker Registry Guide

TeslaOnTarget Docker images are automatically built and published to GitHub Container Registry (ghcr.io).

## Public Access

All images are publicly accessible without authentication:

```bash
docker pull ghcr.io/joshuafuller/teslaontarget:latest
```

## Available Images

### Production Images
- `ghcr.io/joshuafuller/teslaontarget:latest` - Latest stable from main branch
- `ghcr.io/joshuafuller/teslaontarget:v1.0.0` - Specific version
- `ghcr.io/joshuafuller/teslaontarget:v1.0` - Latest v1.0.x
- `ghcr.io/joshuafuller/teslaontarget:v1` - Latest v1.x.x

### Development Images
- `ghcr.io/joshuafuller/teslaontarget:main` - Latest commit on main
- `ghcr.io/joshuafuller/teslaontarget:pr-123` - Pull request #123

## Architecture Support

All images support multiple architectures:
- `linux/amd64` - Standard Intel/AMD 64-bit
- `linux/arm64` - ARM 64-bit (Raspberry Pi 4, Apple Silicon, etc.)

Docker automatically pulls the correct architecture.

## Build Process

### Automatic Builds
GitHub Actions builds and pushes images on:
- Every push to main branch
- Every tagged release (v*)
- Every pull request (no push, build only)

### Manual Trigger
Repository maintainers can trigger builds manually:
1. Go to Actions → Docker Build and Publish
2. Click "Run workflow"
3. Optionally specify a custom tag

### Build Status
[![Docker](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/docker-publish.yml/badge.svg)](https://github.com/joshuafuller/TeslaOnTarget/actions/workflows/docker-publish.yml)

## Security

- Images are scanned for vulnerabilities
- Base image (python:3.9-slim) is regularly updated
- No secrets or credentials in images
- Minimal attack surface with slim base

## Local Development

To build locally matching the CI environment:

```bash
# Standard build
docker build -t teslaontarget:local .

# Multi-platform build (requires buildx)
docker buildx build --platform linux/amd64,linux/arm64 -t teslaontarget:local .
```

## Troubleshooting

### Rate Limits
GitHub Container Registry has generous rate limits:
- Authenticated: 5000 pulls per hour
- Unauthenticated: 100 pulls per hour per IP

### Image Verification
View all available tags:
```bash
# Using Docker Hub API
curl -s https://ghcr.io/v2/joshuafuller/teslaontarget/tags/list

# Using crane tool
crane ls ghcr.io/joshuafuller/teslaontarget
```

### Pull Issues
If you have issues pulling:
1. Check your internet connection
2. Try explicit platform: `docker pull --platform linux/amd64 ghcr.io/joshuafuller/teslaontarget:latest`
3. Check GitHub status: https://www.githubstatus.com/