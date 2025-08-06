# Meeting Transcription Agent MCP Server Dockerfile

FROM python:3.11-slim

# Install system dependencies for audio processing and Whisper
RUN apt-get update && apt-get install -y \
    portaudio19-dev \
    python3-pyaudio \
    alsa-utils \
    pulseaudio \
    ffmpeg \
    build-essential \
    git \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy requirements first for better Docker layer caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy source code
COPY src/ ./src/
COPY *.py ./

# Create directories for logs and data
RUN mkdir -p /app/logs /app/data

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/app/logs/transcription.log
ENV DEFAULT_TRANSCRIPTION_PROVIDER=whisper_local
ENV WHISPER_MODEL_SIZE=base

# Create non-root user for security
RUN useradd -m -u 1001 transcription && \
    chown -R transcription:transcription /app
USER transcription

# Expose port for health checks (if needed)
EXPOSE 8080

# Default command to run the MCP server
CMD ["python", "-m", "src.main"]