#!/bin/bash
set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Function to create config.py from environment variables
create_config() {
    echo -e "${BLUE}Creating configuration from environment variables...${NC}"
    
    # Validate required variables
    if [ -z "$TAK_SERVER" ] && [ "$1" != "auth" ]; then
        echo -e "${RED}ERROR: TAK_SERVER environment variable is required${NC}"
        echo "Example: docker run -e TAK_SERVER=192.168.1.100 ..."
        exit 1
    fi
    
    if [ -z "$TESLA_USERNAME" ] && [ "$1" != "auth" ]; then
        echo -e "${RED}ERROR: TESLA_USERNAME environment variable is required${NC}"
        echo "Example: docker run -e TESLA_USERNAME=your@email.com ..."
        exit 1
    fi
    
    # Create config.py
    cat > /app/config.py << EOF
# Auto-generated configuration from Docker environment variables

# TAK Server Configuration
COT_URL = "tcp://${TAK_SERVER:-localhost}:${TAK_PORT}"

# Tesla Account
TESLA_USERNAME = "${TESLA_USERNAME}"

# Timing Configuration
API_LOOP_DELAY = ${API_LOOP_DELAY}
DEAD_RECKONING_ENABLED = ${DEAD_RECKONING_ENABLED}
DEAD_RECKONING_DELAY = ${DEAD_RECKONING_DELAY}

# File Paths (Docker paths)
LAST_POSITION_FILE = "/data/last_known_position.json"

# Debug Settings
DEBUG_MODE = ${DEBUG_MODE}

# Constants
MPH_TO_MS = 0.44704
EOF
    
    echo -e "${GREEN}✓ Configuration created${NC}"
}

# Function to check if authenticated
is_authenticated() {
    if [ -f "/data/cache.json" ]; then
        # Check if the cache file has content
        if [ -s "/data/cache.json" ]; then
            return 0
        fi
    fi
    return 1
}

# Main logic based on command
case "$1" in
    auth|authenticate)
        echo -e "${BLUE}=== Tesla Authentication ===${NC}"
        echo
        
        if [ -z "$TESLA_USERNAME" ]; then
            echo -e "${YELLOW}Enter your Tesla account email:${NC}"
            read TESLA_USERNAME
            export TESLA_USERNAME
        fi
        
        create_config "auth"
        
        # Link cache file to persistent volume
        # Since we're running as non-root, we need to ensure the link is created in a writable location
        if [ -f /app/cache.json ]; then
            rm -f /app/cache.json
        fi
        ln -sf /data/cache.json /app/cache.json 2>/dev/null || true
        
        echo -e "${BLUE}Starting authentication process...${NC}"
        echo
        echo -e "${YELLOW}Steps:${NC}"
        echo "1. A Tesla login URL will be displayed below"
        echo "2. Copy and paste it into your browser"
        echo "3. Log in with your Tesla account"
        echo "4. You'll see a 'Page Not Found' error - this is normal!"
        echo "5. Copy the ENTIRE URL from your browser"
        echo "6. Paste it back here and press Enter"
        echo
        
        # Run authentication
        cd /app
        python3 -m teslaontarget.auth
        
        if is_authenticated; then
            echo -e "${GREEN}✓ Authentication successful!${NC}"
            echo
            echo "You can now run the container with:"
            echo "docker run -d -e TAK_SERVER=$TAK_SERVER -e TESLA_USERNAME=$TESLA_USERNAME -v tesla_data:/data -v tesla_logs:/logs --name teslaontarget teslaontarget"
        else
            echo -e "${RED}✗ Authentication failed${NC}"
            exit 1
        fi
        ;;
        
    run|start)
        echo -e "${BLUE}=== Starting TeslaOnTarget ===${NC}"
        
        # Create config
        create_config
        
        # Fix permissions on volumes if we can
        # This handles cases where volumes were created by root
        if [ -w /data ]; then
            touch /data/.write_test 2>/dev/null && rm -f /data/.write_test
        else
            echo -e "${YELLOW}Warning: /data is not writable by current user${NC}"
        fi
        
        if [ -w /logs ]; then
            touch /logs/.write_test 2>/dev/null && rm -f /logs/.write_test
        else
            echo -e "${YELLOW}Warning: /logs is not writable by current user${NC}"
            echo -e "${YELLOW}Logs will be written to stdout only${NC}"
        fi
        
        # Link files to persistent volumes
        # Clean up any existing files/links first
        [ -f /app/cache.json ] && rm -f /app/cache.json
        [ -f /app/last_known_position.json ] && rm -f /app/last_known_position.json
        [ -f /app/teslaontarget.log ] && rm -f /app/teslaontarget.log
        [ -L /app/tesla_api_captures ] && rm -f /app/tesla_api_captures
        
        # Create symlinks
        ln -sf /data/cache.json /app/cache.json 2>/dev/null || true
        ln -sf /data/last_known_position.json /app/last_known_position.json 2>/dev/null || true
        
        # Create log file in logs directory (ensure we can write to it)
        touch /logs/teslaontarget.log 2>/dev/null || true
        ln -sf /logs/teslaontarget.log /app/teslaontarget.log 2>/dev/null || true
        
        # If debug mode is enabled, link captures directory
        if [ "$DEBUG_MODE" = "True" ]; then
            mkdir -p /data/tesla_api_captures 2>/dev/null || true
            ln -sf /data/tesla_api_captures /app/tesla_api_captures 2>/dev/null || true
        fi
        
        # Check authentication
        if ! is_authenticated; then
            echo -e "${RED}ERROR: Not authenticated with Tesla${NC}"
            echo
            echo "Please run authentication first:"
            echo "docker run -it -e TESLA_USERNAME=your@email.com -v tesla_data:/data teslaontarget auth"
            exit 1
        fi
        
        echo -e "${GREEN}Configuration:${NC}"
        echo "  Tesla User: $TESLA_USERNAME"
        echo "  TAK Server: $TAK_SERVER:$TAK_PORT"
        echo "  Update Rate: Every ${API_LOOP_DELAY}s"
        echo "  Dead Reckoning: $DEAD_RECKONING_ENABLED"
        echo "  Debug Mode: $DEBUG_MODE"
        echo
        
        # Start the application
        echo -e "${GREEN}✓ Starting vehicle tracking...${NC}"
        cd /app
        exec python3 -m teslaontarget
        ;;
        
    test)
        echo -e "${BLUE}=== Testing Configuration ===${NC}"
        create_config
        
        # Test TAK server connectivity
        echo -e "${BLUE}Testing TAK server connection...${NC}"
        if timeout 5 bash -c "echo >/dev/tcp/${TAK_SERVER}/${TAK_PORT}" 2>/dev/null; then
            echo -e "${GREEN}✓ TAK server is reachable${NC}"
        else
            echo -e "${RED}✗ Cannot connect to TAK server at ${TAK_SERVER}:${TAK_PORT}${NC}"
            exit 1
        fi
        
        # Check authentication
        if is_authenticated; then
            echo -e "${GREEN}✓ Tesla authentication found${NC}"
        else
            echo -e "${YELLOW}⚠ Not authenticated with Tesla${NC}"
        fi
        
        echo -e "${GREEN}✓ Configuration test complete${NC}"
        ;;
        
    shell|bash)
        # For debugging
        create_config
        exec /bin/bash
        ;;
        
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo
        echo "Usage:"
        echo "  docker run -it ... teslaontarget auth    # Authenticate with Tesla"
        echo "  docker run -d ... teslaontarget run      # Run the tracker"
        echo "  docker run -it ... teslaontarget test    # Test configuration"
        exit 1
        ;;
esac