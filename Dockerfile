# Meeting Transcription Agent MCP Server
FROM python:3.11-slim

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    gosu \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY src/ ./src/
COPY fix-permissions.sh /usr/local/bin/fix-permissions.sh
RUN chmod +x /usr/local/bin/fix-permissions.sh

# Set environment variables
ENV PYTHONPATH=/app
ENV WHISPER_MODEL_SIZE=base
ENV HF_HOME=/app/.cache
ENV HUGGINGFACE_HUB_CACHE=/app/.cache
ENV TRANSFORMERS_CACHE=/app/.cache

# Create directories with proper permissions
RUN mkdir -p /app/logs /app/data/transcriptions /app/.cache && \
    chown -R 1000:1000 /app

# Simple startup - run from src directory
WORKDIR /app/src
CMD ["/usr/local/bin/fix-permissions.sh"]