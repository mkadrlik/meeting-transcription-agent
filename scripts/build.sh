#!/bin/bash
# Simple build and test script

set -e

echo "🏗️ Building Fast Whisper MCP Server..."

# Build and start
docker compose build
docker compose up -d

# Wait for health check
echo "⏳ Waiting for service..."
sleep 10

# Test
echo "🧪 Testing service..."
docker compose exec fast-whisper-mcp python scripts/test.py

echo "✅ Fast Whisper MCP Server is ready!"
echo "📁 Transcriptions will be saved to: /DATA/san-raid5/AppData/meeting-transcription-agent/data/transcriptions/"