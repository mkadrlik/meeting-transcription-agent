#!/bin/bash
# Complete Meeting Recording Solution
# Starts Docker MCP Server + Host Audio Bridge

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎤🔊 Complete Meeting Recording Solution${NC}"
echo "=========================================="
echo "Docker MCP Server + DUAL Audio Bridge"
echo "📱 Captures: Microphone + Bluetooth Headphone Output"
echo ""

# Get script directory
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# Function to check if MCP server is running
check_mcp_server() {
    echo -e "${YELLOW}🔍 Checking MCP server status...${NC}"
    
    if curl -s http://192.168.50.20:9000/health >/dev/null 2>&1; then
        echo -e "${GREEN}✅ MCP server is already running${NC}"
        return 0
    else
        echo -e "${YELLOW}⚠️ MCP server not running${NC}"
        return 1
    fi
}

# Function to start MCP server
start_mcp_server() {
    echo -e "${BLUE}🚀 Starting Docker MCP server...${NC}"
    
    # Start the Docker containers
    ./scripts/run.sh start
    
    # Wait for server to be ready
    echo -e "${YELLOW}⏳ Waiting for MCP server to start...${NC}"
    
    for i in {1..30}; do
        if curl -s http://192.168.50.20:9000/health >/dev/null 2>&1; then
            echo -e "${GREEN}✅ MCP server is ready!${NC}"
            return 0
        fi
        sleep 2
        echo -n "."
    done
    
    echo -e "${RED}❌ MCP server failed to start after 60 seconds${NC}"
    return 1
}

# Function to start audio bridge
start_audio_bridge() {
    echo -e "${BLUE}🎤🔊 Starting DUAL audio bridge...${NC}"
    echo ""
    echo -e "${GREEN}📱 Captures both sides of your meeting:${NC}"
    echo -e "${GREEN}  🎤 Your microphone (your voice)${NC}"
    echo -e "${GREEN}  🔊 Speaker output (other participants via Bluetooth)${NC}"
    echo ""
    echo -e "${YELLOW}Press Ctrl+C when your meeting is finished${NC}"
    echo ""
    
    # Install host requirements if needed
    echo -e "${BLUE}📦 Installing host requirements...${NC}"
    if [ -f "requirements-host.txt" ]; then
        pip3 install --user -q -r requirements-host.txt
    else
        echo -e "${YELLOW}⚠️ requirements-host.txt not found, installing basic deps${NC}"
        pip3 install --user pyaudio requests numpy
    fi
    
    # Start the audio bridge
    python3 src/audio/host_bridge.py --gateway-url http://192.168.50.20:9000
}

# Main execution
main() {
    echo -e "${BLUE}Step 1: Ensuring MCP Server is running${NC}"
    
    if ! check_mcp_server; then
        if ! start_mcp_server; then
            echo -e "${RED}❌ Failed to start MCP server${NC}"
            exit 1
        fi
    fi
    
    echo ""
    echo -e "${BLUE}Step 2: Starting Audio Bridge${NC}"
    
    start_audio_bridge
}

# Handle script arguments
case "${1:-start}" in
    "start"|"")
        main
        ;;
    "stop")
        echo -e "${YELLOW}🛑 Stopping meeting recording services...${NC}"
        ./scripts/run.sh stop
        echo -e "${GREEN}✅ Services stopped${NC}"
        ;;
    "status")
        check_mcp_server
        ./scripts/run.sh status
        ;;
    "help"|"-h"|"--help")
        echo "Usage: $0 [COMMAND]"
        echo ""
        echo "Commands:"
        echo "  start     Start complete recording solution (default)"
        echo "  stop      Stop all services"  
        echo "  status    Check service status"
        echo "  help      Show this help message"
        echo ""
        echo "The 'start' command will:"
        echo "1. Start Docker MCP server (if not running)"
        echo "2. Launch DUAL audio bridge (mic + speaker)"
        echo "3. Begin live meeting transcription with both sides"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac