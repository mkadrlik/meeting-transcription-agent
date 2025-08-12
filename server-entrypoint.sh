#!/bin/bash
# Server entrypoint that keeps the container running for healthchecks
# while still allowing MCP functionality

# Fix permissions first
if [ -d "/app/host-data" ]; then
    echo "Fixing permissions for /app/host-data"
    chown -R 1000:1000 /app/host-data
    chmod -R 755 /app/host-data
fi

# For server deployments, we need to keep the container running
# but still allow MCP connections when needed
echo "Meeting Transcription Agent MCP Server ready for connections"
echo "Container will stay running for healthchecks and on-demand MCP connections"

# Keep container running while allowing MCP server to be invoked
while true; do
    sleep 30
    # Verify the MCP server can still initialize (for healthcheck purposes)
    if ! gosu 1000:1000 python -c "import sys; sys.path.insert(0, '/app/src'); from transcription.service import MeetingTranscriptionService; print('MCP server components healthy')" > /dev/null 2>&1; then
        echo "ERROR: MCP server components unhealthy"
        exit 1
    fi
done