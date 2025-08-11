#!/bin/bash
# Meeting Transcription Agent - Server Only
# Starts Docker MCP Server for client-side audio forwarding

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}🎤 Meeting Transcription Agent - Server${NC}"
echo "========================================"
echo "Docker MCP Server for Client Audio Forwarding"
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

# Main execution
main() {
    echo -e "${BLUE}Starting MCP Server${NC}"
    
    if ! check_mcp_server; then
        if ! start_mcp_server; then
            echo -e "${RED}❌ Failed to start MCP server${NC}"
            exit 1
        fi
    fi
    
    echo ""
    echo -e "${GREEN}✅ Server is ready for client audio forwarding${NC}"
    echo ""
    echo -e "${BLUE}Next steps:${NC}"
    echo -e "${BLUE}1. Use MCP tools to start client recording sessions${NC}"
    echo -e "${BLUE}2. Send audio chunks from your client application${NC}"
    echo -e "${BLUE}3. Get transcriptions when finished${NC}"
}

# Handle script arguments
case "${1:-start}" in
    "start"|"")
        main
        ;;
    "stop")
        echo -e "${YELLOW}🛑 Stopping meeting transcription services...${NC}"
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
        echo "  start     Start server (default)"
        echo "  stop      Stop all services"  
        echo "  status    Check service status"
        echo "  help      Show this help message"
        echo ""
        echo "The 'start' command will:"
        echo "1. Start Docker MCP server (if not running)"
        echo "2. Ready for client audio forwarding"
        ;;
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo "Use '$0 help' for usage information"
        exit 1
        ;;
esac