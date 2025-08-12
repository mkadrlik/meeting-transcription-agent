# Meeting Transcription Agent MCP Server Dockerfile

FROM python:3.11-slim

# Install system dependencies for Whisper processing only
RUN apt-get update && apt-get install -y \
    ffmpeg \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies (excluding PyAudio for client-forwarding mode)
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY *.py ./

# Create directories for logs, data, and cache
RUN mkdir -p /app/logs /app/data /app/.cache/whisper

# Pre-download Whisper model during build
RUN python scripts/init-whisper.py

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/app/logs/transcription.log
ENV DEFAULT_TRANSCRIPTION_PROVIDER=whisper_local
ENV WHISPER_MODEL_SIZE=base

# Make scripts executable
RUN chmod +x scripts/*.py scripts/*.sh

# Create non-root user for security
RUN useradd -m -u 1001 transcription && \
    chown -R transcription:transcription /app
USER transcription

# Expose port for health checks (if needed)
EXPOSE 8080

# Use entrypoint script to ensure model availability
ENTRYPOINT ["/app/scripts/entrypoint.sh"]

# Default command to run the MCP server
CMD ["python", "-m", "src.main"]