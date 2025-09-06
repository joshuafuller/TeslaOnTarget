#!/bin/bash
# TeslaOnTarget Control Script - Start, Stop, and Status in one script

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$SCRIPT_DIR"
LOG_FILE="$PROJECT_DIR/teslaontarget.log"
PID_FILE="$PROJECT_DIR/teslaontarget.pid"

# Color codes for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[0;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to check if running
is_running() {
    if [ -f "$PID_FILE" ]; then
        PID=$(cat "$PID_FILE")
        if ps -p $PID > /dev/null 2>&1; then
            return 0  # Running
        else
            # Stale PID file
            rm -f "$PID_FILE"
            return 1  # Not running
        fi
    else
        return 1  # Not running
    fi
}

# Function to start TeslaOnTarget
start_tesla() {
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "${YELLOW}TeslaOnTarget is already running with PID $PID${NC}"
        exit 1
    fi

    echo -e "${BLUE}Starting TeslaOnTarget...${NC}"
    echo "Log file: $LOG_FILE"

    # Change to project directory
    cd "$PROJECT_DIR"

    # Start in background with logging
    nohup python3 -m teslaontarget >> "$LOG_FILE" 2>&1 &
    PID=$!

    # Save PID
    echo $PID > "$PID_FILE"

    # Wait a moment to check if it started successfully
    sleep 2
    if is_running; then
        echo -e "${GREEN}✓ TeslaOnTarget started successfully with PID $PID${NC}"
        echo -e "To view logs: tail -f $LOG_FILE"
    else
        echo -e "${RED}✗ Failed to start TeslaOnTarget${NC}"
        echo "Check the log file for errors: tail -20 $LOG_FILE"
        exit 1
    fi
}

# Function to stop TeslaOnTarget
stop_tesla() {
    if ! is_running; then
        echo -e "${YELLOW}TeslaOnTarget is not running${NC}"
        exit 1
    fi

    PID=$(cat "$PID_FILE")
    echo -e "${BLUE}Stopping TeslaOnTarget (PID $PID)...${NC}"
    
    # Try graceful shutdown first
    kill $PID 2>/dev/null
    
    # Wait up to 5 seconds for graceful shutdown
    for i in {1..5}; do
        if ! ps -p $PID > /dev/null 2>&1; then
            break
        fi
        sleep 1
    done
    
    # Force kill if still running
    if ps -p $PID > /dev/null 2>&1; then
        echo -e "${YELLOW}Force killing...${NC}"
        kill -9 $PID 2>/dev/null
    fi
    
    rm -f "$PID_FILE"
    echo -e "${GREEN}✓ TeslaOnTarget stopped${NC}"
}

# Function to show status
show_status() {
    echo -e "${BLUE}TeslaOnTarget Status${NC}"
    echo "===================="
    
    if is_running; then
        PID=$(cat "$PID_FILE")
        echo -e "Status: ${GREEN}RUNNING${NC}"
        echo "PID: $PID"
        echo ""
        echo "Process info:"
        ps -fp $PID
        echo ""
        
        # Show connection status from recent logs
        if [ -f "$LOG_FILE" ]; then
            echo "Recent activity:"
            # Get last few relevant log lines
            tail -20 "$LOG_FILE" | grep -E "(Connected to TAK|Got vehicle data|Dead reckoning|ERROR|WARNING)" | tail -5
        fi
    else
        echo -e "Status: ${RED}NOT RUNNING${NC}"
    fi
}

# Function to restart TeslaOnTarget
restart_tesla() {
    echo -e "${BLUE}Restarting TeslaOnTarget...${NC}"
    if is_running; then
        stop_tesla
        sleep 2
    fi
    start_tesla
}

# Function to show logs
show_logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo -e "${RED}Log file not found: $LOG_FILE${NC}"
        exit 1
    fi
}

# Function to show help
show_help() {
    echo "TeslaOnTarget Control Script"
    echo ""
    echo "Usage: $0 {start|stop|restart|status|logs|help}"
    echo ""
    echo "Commands:"
    echo "  start    - Start TeslaOnTarget in the background"
    echo "  stop     - Stop TeslaOnTarget"
    echo "  restart  - Restart TeslaOnTarget"
    echo "  status   - Show current status"
    echo "  logs     - Follow the log file (tail -f)"
    echo "  help     - Show this help message"
    echo ""
    echo "Configuration:"
    echo "  Edit config.py to set your Tesla account and TAK server details"
    echo ""
    echo "Examples:"
    echo "  $0 start      # Start tracking"
    echo "  $0 status     # Check if running"
    echo "  $0 logs       # View live logs"
    echo "  $0 stop       # Stop tracking"
}

# Main script logic
case "$1" in
    start)
        start_tesla
        ;;
    stop)
        stop_tesla
        ;;
    restart)
        restart_tesla
        ;;
    status)
        show_status
        ;;
    logs)
        show_logs
        ;;
    help|--help|-h)
        show_help
        ;;
    *)
        if [ -z "$1" ]; then
            # No arguments - show status
            show_status
        else
            echo -e "${RED}Unknown command: $1${NC}"
            echo ""
            show_help
            exit 1
        fi
        ;;
esac