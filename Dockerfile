# syntax=docker/dockerfile:1.4

# Build stage
FROM python:3.13-slim AS builder

# Install build dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Set up build directory
WORKDIR /build

# Copy and install dependencies
COPY requirements.txt .
RUN pip wheel --no-cache-dir --no-deps --wheel-dir /build/wheels -r requirements.txt

# Runtime stage
FROM python:3.13-slim

# Add metadata labels
LABEL org.opencontainers.image.title="TeslaOnTarget" \
      org.opencontainers.image.description="Bridge Tesla vehicles with TAK servers for real-time position tracking" \
      org.opencontainers.image.authors="Joshua Fuller" \
      org.opencontainers.image.source="https://github.com/joshuafuller/TeslaOnTarget" \
      org.opencontainers.image.licenses="MIT"

# Create non-root user
RUN useradd -m -s /bin/bash -u 1000 teslauser && \
    mkdir -p /data /logs /app && \
    chown -R teslauser:teslauser /data /logs /app

WORKDIR /app

# Copy wheels from builder and install
COPY --from=builder /build/wheels /wheels
RUN pip install --no-cache-dir /wheels/* && rm -rf /wheels

# Copy application files with correct ownership
COPY --chown=teslauser:teslauser . .

# Install the package
RUN pip install --no-cache-dir -e .

# Move entrypoint to root and ensure it's executable
RUN cp /app/docker-entrypoint.sh / && chmod +x /docker-entrypoint.sh

# Switch to non-root user
USER teslauser

# Environment variables for configuration
ENV TESLA_USERNAME="" \
    TAK_SERVER="" \
    TAK_PORT="8085" \
    API_LOOP_DELAY="10" \
    DEAD_RECKONING_ENABLED="True" \
    DEAD_RECKONING_DELAY="1" \
    DEBUG_MODE="False" \
    VEHICLE_FILTER=""

# Health check - directly call python to bypass entrypoint
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["/usr/local/bin/python", "-c", "import teslaontarget; print('healthy')"]

# Volumes for persistent data
VOLUME ["/data", "/logs"]

# No EXPOSE needed as we're a client, not a server

# Default command
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run"]