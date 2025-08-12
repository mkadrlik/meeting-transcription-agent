#!/bin/bash
# Meeting Transcription Agent Entrypoint Script
# Ensures Whisper model is available before starting the MCP server

set -e

echo "🎤 Meeting Transcription Agent - Starting..."

# Set cache directories
export HF_HOME=/app/.cache
export TRANSFORMERS_CACHE=/app/.cache
export WHISPER_CACHE_DIR=/app/.cache/whisper
export HOME=/app

# Ensure cache directories exist and are writable
mkdir -p /app/.cache/whisper
chmod -R 755 /app/.cache

echo "📁 Cache directories configured:"
echo "  HF_HOME: $HF_HOME"
echo "  WHISPER_CACHE_DIR: $WHISPER_CACHE_DIR"

# Check if Whisper model is available
echo "🔍 Checking Whisper model availability..."
python -c "
import whisper
import os
model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')
print(f'Loading Whisper model: {model_size}')
model = whisper.load_model(model_size)
print(f'✅ Whisper model {model_size} is ready')
"

if [ $? -eq 0 ]; then
    echo "✅ Whisper model verification successful"
else
    echo "❌ Whisper model verification failed"
    echo "🔄 Attempting to download model..."
    python /app/scripts/init-whisper.py
    
    if [ $? -ne 0 ]; then
        echo "❌ Failed to initialize Whisper model"
        exit 1
    fi
fi

echo "🚀 Starting MCP server..."
exec "$@"