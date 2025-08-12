# Fast Whisper MCP Server - Simplified
FROM python:3.11-slim

# Install only essential system dependencies
RUN apt-get update && apt-get install -y \
    ffmpeg \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Copy and install requirements
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/

# Create directories
RUN mkdir -p /app/logs /app/data/transcriptions /app/.cache

# Set environment variables
ENV PYTHONPATH=/app
ENV WHISPER_MODEL_SIZE=base

# Create non-root user
RUN useradd -m -u 1001 transcription && \
    chown -R transcription:transcription /app
USER transcription

# Simple startup
CMD ["python", "-m", "src.main"]