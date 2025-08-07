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

# Function to check system dependencies
check_system_deps() {
    echo -e "${BLUE}🔍 Checking system dependencies...${NC}"
    local missing_deps=()
    
    # Check for PortAudio headers
    if ! pkg-config --exists portaudio-2.0 2>/dev/null && [ ! -f "/usr/include/portaudio.h" ] && [ ! -f "/usr/local/include/portaudio.h" ]; then
        missing_deps+=("portaudio development headers")
    fi
    
    # Check for Python development headers
    local python_version=$(python3 -c "import sys; print(f'{sys.version_info.major}.{sys.version_info.minor}')")
    if [ ! -f "/usr/include/python${python_version}/Python.h" ] && [ ! -f "/usr/local/include/python${python_version}/Python.h" ]; then
        missing_deps+=("python${python_version} development headers")
    fi
    
    if [ ${#missing_deps[@]} -eq 0 ]; then
        echo -e "${GREEN}✅ All system dependencies are installed${NC}"
        return 0
    fi
    
    echo -e "${RED}❌ Missing system dependencies:${NC}"
    for dep in "${missing_deps[@]}"; do
        echo -e "${RED}  - $dep${NC}"
    done
    echo ""
    echo -e "${YELLOW}💡 Install missing dependencies:${NC}"
    
    # Detect package manager and provide appropriate commands
    if command -v apt >/dev/null 2>&1; then
        echo -e "${BLUE}For Ubuntu/Debian:${NC}"
        echo -e "${GREEN}sudo apt update && sudo apt install -y portaudio19-dev python${python_version}-dev${NC}"
    elif command -v yum >/dev/null 2>&1; then
        echo -e "${BLUE}For CentOS/RHEL:${NC}"
        echo -e "${GREEN}sudo yum install -y portaudio-devel python${python_version}-devel${NC}"
    elif command -v dnf >/dev/null 2>&1; then
        echo -e "${BLUE}For Fedora:${NC}"
        echo -e "${GREEN}sudo dnf install -y portaudio-devel python${python_version}-devel${NC}"
    elif command -v pacman >/dev/null 2>&1; then
        echo -e "${BLUE}For Arch Linux:${NC}"
        echo -e "${GREEN}sudo pacman -S portaudio python-dev${NC}"
    else
        echo -e "${YELLOW}Please install PortAudio and Python development headers for your distribution${NC}"
    fi
    echo ""
    echo -e "${YELLOW}Then run this script again.${NC}"
    
    return 1
}

# Function to setup virtual environment
setup_venv() {
    local venv_dir=".venv-host"
    
    # Check if python3 is available
    if ! command -v python3 >/dev/null 2>&1; then
        echo -e "${RED}❌ python3 not found. Please install Python 3${NC}"
        return 1
    fi
    
    # Create virtual environment if it doesn't exist
    if [ ! -d "$venv_dir" ]; then
        echo -e "${BLUE}🔧 Creating virtual environment...${NC}"
        if ! python3 -m venv "$venv_dir" 2>/dev/null; then
            echo -e "${RED}❌ Failed to create virtual environment${NC}"
            echo -e "${YELLOW}💡 Try installing python3-venv: sudo apt install python3-venv${NC}"
            return 1
        fi
    fi
    
    # Check if activation script exists
    if [ ! -f "$venv_dir/bin/activate" ]; then
        echo -e "${RED}❌ Virtual environment activation script not found${NC}"
        echo -e "${YELLOW}💡 Removing corrupted venv and retrying...${NC}"
        rm -rf "$venv_dir"
        if ! python3 -m venv "$venv_dir" 2>/dev/null; then
            echo -e "${RED}❌ Failed to recreate virtual environment${NC}"
            return 1
        fi
    fi
    
    echo -e "${BLUE}🔄 Activating virtual environment...${NC}"
    source "$venv_dir/bin/activate"
    
    # Verify activation worked
    if [ "$VIRTUAL_ENV" = "" ]; then
        echo -e "${RED}❌ Failed to activate virtual environment${NC}"
        return 1
    fi
    
    # Upgrade pip to latest version
    pip install --upgrade pip >/dev/null 2>&1
    
    return 0
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
    
    # Check system dependencies first
    if ! check_system_deps; then
        echo -e "${RED}❌ System dependencies not met${NC}"
        exit 1
    fi
    
    # Setup virtual environment
    if ! setup_venv; then
        echo -e "${RED}❌ Failed to setup virtual environment${NC}"
        exit 1
    fi
    
    # Install host requirements if needed
    echo -e "${BLUE}📦 Installing host requirements in virtual environment...${NC}"
    if [ -f "requirements-host.txt" ]; then
        pip install -q -r requirements-host.txt
    else
        echo -e "${YELLOW}⚠️ requirements-host.txt not found, installing basic deps${NC}"
        pip install pyaudio requests numpy
    fi
    
    # Start the audio bridge using virtual environment python
    python src/audio/host_bridge.py --gateway-url http://192.168.50.20:9000
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