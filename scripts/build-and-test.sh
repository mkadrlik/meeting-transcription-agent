#!/bin/bash
# Build and test the meeting transcription agent with Whisper model

set -e

echo "🏗️ Building Meeting Transcription Agent..."

# Clean up any existing containers
docker compose down --remove-orphans

# Build with no cache to ensure fresh build
echo "📦 Building Docker image..."
docker compose build --no-cache

# Start the service
echo "🚀 Starting service..."
docker compose up -d

# Wait for service to be healthy
echo "⏳ Waiting for service to be ready..."
for i in {1..30}; do
    if docker compose ps | grep -q "healthy"; then
        echo "✅ Service is healthy!"
        break
    elif [ $i -eq 30 ]; then
        echo "❌ Service failed to become healthy"
        docker compose logs
        exit 1
    else
        echo "Waiting... ($i/30)"
        sleep 2
    fi
done

# Test Whisper model
echo "🧪 Testing Whisper model..."
docker compose exec meeting-transcription python scripts/test-whisper.py

if [ $? -eq 0 ]; then
    echo "✅ All tests passed!"
    echo "🎉 Meeting Transcription Agent is ready with Whisper model"
else
    echo "❌ Tests failed"
    docker compose logs
    exit 1
fi

echo ""
echo "📋 Service Status:"
docker compose ps

echo ""
echo "🔗 Service is running and ready for MCP connections"
echo "   Cache directory: /DATA/san-raid5/AppData/meeting-transcription-agent/cache"
echo "   Logs directory: /DATA/san-raid5/AppData/meeting-transcription-agent/logs"