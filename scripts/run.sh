#!/bin/bash
# Meeting Transcription Agent MCP Server - Run Script

set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

echo -e "${BLUE}Meeting Transcription Agent MCP Server${NC}"
echo "======================================="

# Get the directory containing this script
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

# Get the repository root directory (parent of scripts directory)
REPO_ROOT="$(dirname "$SCRIPT_DIR")"

# Change to repository root directory
cd "$REPO_ROOT"

echo "Working from repository root: $(pwd)"

# Check if Docker is installed
if ! command -v docker &> /dev/null; then
    echo -e "${RED}Error: Docker is not installed or not in PATH${NC}"
    echo "Please install Docker first: https://docs.docker.com/get-docker/"
    exit 1
fi

# Check if Docker Compose is installed
if ! command -v docker compose &> /dev/null && ! docker compose version &> /dev/null; then
    echo -e "${RED}Error: Docker Compose is not installed${NC}"
    echo "Please install Docker Compose: https://docs.docker.com/compose/install/"
    exit 1
fi

# Check if .env file exists in repository root
if [ ! -f .env ]; then
    echo -e "${YELLOW}Warning: .env file not found in repository root${NC}"
    
    if [ -f .env.example ]; then
        echo "Creating .env file from template..."
        cp .env.example .env
        echo -e "${GREEN}.env file created successfully${NC}"
        echo -e "${YELLOW}Please edit .env file to configure your settings before starting${NC}"
        echo ""
        read -p "Press Enter to continue or Ctrl+C to exit and edit .env file..."
    else
        echo -e "${RED}Error: .env.example file not found in repository root${NC}"
        echo "Please ensure you're running this script from the correct location."
        exit 1
    fi
fi

# Create necessary directories
echo "Creating necessary directories..."
mkdir -p logs data

# Function to show usage
show_usage() {
    echo "Usage: $0 [COMMAND]"
    echo ""
    echo "Commands:"
    echo "  start     Start the services"
    echo "  stop      Stop the services"
    echo "  restart   Restart the services"
    echo "  logs      Show logs"
    echo "  status    Show service status"
    echo "  build     Build the Docker image"
    echo "  clean     Stop services and remove containers"
    echo "  help      Show this help message"
}

# Main command handling
case "${1:-start}" in
    "start")
        echo -e "${GREEN}Starting Meeting Transcription Agent...${NC}"
        docker compose up -d
        echo ""
        echo -e "${GREEN}Services started successfully!${NC}"docker mcp 
        echo "- MCP Gateway: http://localhost:8080"
        echo "- Logs: docker compose logs -f"
        echo "- Status: ./scripts/run.sh status"
        ;;
    
    "stop")
        echo -e "${YELLOW}Stopping services...${NC}"
        docker compose down
        echo -e "${GREEN}Services stopped${NC}"
        ;;
    
    "restart")
        echo -e "${YELLOW}Restarting services...${NC}"
        docker compose down
        docker compose up -d
        echo -e "${GREEN}Services restarted${NC}"
        ;;
    
    "logs")
        echo -e "${BLUE}Showing logs (Ctrl+C to exit)...${NC}"
        docker compose logs -f
        ;;
    
    "status")
        echo -e "${BLUE}Service Status:${NC}"
        docker compose ps
        ;;
    
    "build")
        echo -e "${BLUE}Building Docker image...${NC}"
        docker compose build
        echo -e "${GREEN}Build completed${NC}"
        ;;
    
    "clean")
        echo -e "${YELLOW}Stopping and removing containers...${NC}"
        docker compose down --rmi local --volumes
        echo -e "${GREEN}Cleanup completed${NC}"
        ;;
    
    "help"|"-h"|"--help")
        show_usage
        ;;
    
    *)
        echo -e "${RED}Unknown command: $1${NC}"
        echo ""
        show_usage
        exit 1
        ;;
esac