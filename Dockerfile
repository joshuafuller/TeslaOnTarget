# Use Python slim image for smaller size
FROM python:3.13-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first for better caching
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the entire project
COPY . .

# Install the package
RUN pip install -e .

# Create directories for persistent data
RUN mkdir -p /data /logs

# Environment variables for configuration
ENV TESLA_USERNAME=""
ENV TAK_SERVER=""
ENV TAK_PORT="8085"
ENV API_LOOP_DELAY="10"
ENV DEAD_RECKONING_ENABLED="True"
ENV DEAD_RECKONING_DELAY="1"
ENV DEBUG_MODE="False"

# Volume for persistent data (cache.json, logs, captures)
VOLUME ["/data", "/logs"]

# Copy entrypoint script
COPY docker-entrypoint.sh /
RUN chmod +x /docker-entrypoint.sh

# Default command
ENTRYPOINT ["/docker-entrypoint.sh"]
CMD ["run"]