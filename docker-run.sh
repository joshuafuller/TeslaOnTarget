#!/bin/bash
# Convenient Docker commands for TeslaOnTarget

# Color codes
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m'

# Check if .env exists
if [ ! -f .env ]; then
    echo -e "${RED}ERROR: .env file not found!${NC}"
    echo "Copy .env.example to .env and update with your settings"
    exit 1
fi

case "$1" in
    auth)
        echo -e "${BLUE}Starting Tesla authentication...${NC}"
        docker run -it --env-file .env -v tesla_data:/data teslaontarget auth
        ;;
    
    start)
        echo -e "${BLUE}Starting TeslaOnTarget...${NC}"
        docker run -d \
            --env-file .env \
            -v tesla_data:/data \
            -v tesla_logs:/logs \
            --name teslaontarget \
            --restart unless-stopped \
            teslaontarget
        echo -e "${GREEN}✓ Started! View logs with: $0 logs${NC}"
        ;;
    
    stop)
        echo -e "${BLUE}Stopping TeslaOnTarget...${NC}"
        docker stop teslaontarget
        docker rm teslaontarget
        echo -e "${GREEN}✓ Stopped${NC}"
        ;;
    
    restart)
        $0 stop
        sleep 2
        $0 start
        ;;
    
    logs)
        docker logs -f teslaontarget
        ;;
    
    status)
        if docker ps | grep -q teslaontarget; then
            echo -e "${GREEN}✓ TeslaOnTarget is running${NC}"
            echo ""
            docker ps --filter name=teslaontarget --format "table {{.Status}}\t{{.Ports}}"
            echo ""
            echo "Recent logs:"
            docker logs --tail 5 teslaontarget
        else
            echo -e "${RED}✗ TeslaOnTarget is not running${NC}"
        fi
        ;;
    
    test)
        echo -e "${BLUE}Testing configuration...${NC}"
        docker run --rm --env-file .env -v tesla_data:/data teslaontarget test
        ;;
    
    shell)
        echo -e "${BLUE}Opening shell in container...${NC}"
        docker run -it --rm \
            --env-file .env \
            -v tesla_data:/data \
            -v tesla_logs:/logs \
            teslaontarget shell
        ;;
    
    build)
        echo -e "${BLUE}Building Docker image...${NC}"
        docker build -t teslaontarget .
        ;;
    
    *)
        echo "TeslaOnTarget Docker Helper"
        echo ""
        echo "Usage: $0 {auth|start|stop|restart|logs|status|test|shell|build}"
        echo ""
        echo "Commands:"
        echo "  auth     - Authenticate with Tesla (run this first)"
        echo "  start    - Start TeslaOnTarget in background"
        echo "  stop     - Stop TeslaOnTarget"
        echo "  restart  - Restart TeslaOnTarget"
        echo "  logs     - View live logs"
        echo "  status   - Check if running"
        echo "  test     - Test configuration"
        echo "  shell    - Open shell for debugging"
        echo "  build    - Rebuild Docker image"
        ;;
esac