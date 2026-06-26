# syntax=docker/dockerfile:1.4

# ---- Build stage: resolve + install deps with uv into /app/.venv ----
FROM python:3.14-slim AS builder

# uv: fast, reproducible installs from uv.lock
COPY --from=ghcr.io/astral-sh/uv:latest /uv /uvx /bin/

ENV UV_COMPILE_BYTECODE=1 \
    UV_LINK_MODE=copy

WORKDIR /app

# Install dependencies first (cached layer keyed on the lockfile)
COPY pyproject.toml uv.lock ./
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-install-project --no-dev

# Install the project itself
COPY . .
RUN --mount=type=cache,target=/root/.cache/uv \
    uv sync --frozen --no-dev

# ---- Runtime stage ----
FROM python:3.14-slim

LABEL org.opencontainers.image.title="TeslaOnTarget" \
      org.opencontainers.image.description="Bridge Tesla vehicles with TAK servers for real-time position tracking" \
      org.opencontainers.image.authors="Joshua Fuller" \
      org.opencontainers.image.source="https://github.com/joshuafuller/TeslaOnTarget" \
      org.opencontainers.image.licenses="MIT"

# Non-root runtime user
RUN useradd -m -s /bin/bash -u 1000 teslauser && \
    mkdir -p /data /logs /app && \
    chown -R teslauser:teslauser /data /logs /app

WORKDIR /app

# Copy the fully-provisioned app (source + /app/.venv) from the builder
COPY --from=builder --chown=teslauser:teslauser /app /app

# Put the venv on PATH so `python`/`python3` resolve to it, and point the config
# loader at an explicit path so it never depends on the package install layout.
ENV PATH="/app/.venv/bin:$PATH" \
    TESLAONTARGET_CONFIG="/app/config.py" \
    TESLA_USERNAME="" \
    TAK_SERVER="" \
    TAK_PORT="8085" \
    API_LOOP_DELAY="10" \
    DEAD_RECKONING_ENABLED="True" \
    DEAD_RECKONING_DELAY="1" \
    DEBUG_MODE="False" \
    VEHICLE_FILTER=""

RUN cp /app/docker-entrypoint.sh / && chmod +x /docker-entrypoint.sh

USER teslauser

HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD ["python", "-c", "import teslaontarget; print('healthy')"]

VOLUME ["/data", "/logs"]

ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run"]
