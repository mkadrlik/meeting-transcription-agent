#!/bin/bash
# Setup host directories with proper permissions for Fast Whisper MCP Server

set -e

echo "🔧 Setting up host directories for Fast Whisper MCP Server..."

# Create directories
echo "Creating directories..."
sudo mkdir -p /DATA/san-raid5/AppData/meeting-transcription-agent/data/transcriptions
sudo mkdir -p /DATA/san-raid5/AppData/meeting-transcription-agent/cache

# Set ownership to user 1000:1000 (matches container user)
echo "Setting ownership to 1000:1000..."
sudo chown -R 1000:1000 /DATA/san-raid5/AppData/meeting-transcription-agent/

# Set permissions
echo "Setting permissions..."
sudo chmod -R 755 /DATA/san-raid5/AppData/meeting-transcription-agent/

echo "✅ Host directories setup complete!"
echo ""
echo "Directory structure:"
echo "📁 /DATA/san-raid5/AppData/meeting-transcription-agent/"
echo "  ├── 📁 data/transcriptions/  (for transcript output files)"
echo "  └── 📁 cache/               (for Whisper model cache)"
echo ""
echo "Now you can run: docker compose up -d"