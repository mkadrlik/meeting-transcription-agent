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

# Set environment variables to prevent PyTorch ARM64 issues
ENV PYTORCH_DISABLE_CUDNN_WARNINGS=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1

# Install CPU-only PyTorch first to avoid ARM64 issues
RUN PYTORCH_DISABLE_CUDNN_WARNINGS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    pip install --no-cache-dir torch torchvision torchaudio --index-url https://download.pytorch.org/whl/cpu

# Install Python dependencies (excluding PyAudio for client-forwarding mode)
RUN PYTORCH_DISABLE_CUDNN_WARNINGS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    pip install --no-cache-dir -r requirements.txt

# Copy source code and scripts
COPY src/ ./src/
COPY scripts/ ./scripts/
COPY *.py ./

# Create directories for logs, data, and cache
RUN mkdir -p /app/logs /app/data /app/.cache/whisper

# Test PyTorch compatibility first
RUN PYTORCH_DISABLE_CUDNN_WARNINGS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    python scripts/test-pytorch.py

# Pre-download Whisper model during build with error handling
RUN PYTORCH_DISABLE_CUDNN_WARNINGS=1 OMP_NUM_THREADS=1 MKL_NUM_THREADS=1 \
    python scripts/init-whisper.py || echo "Warning: Whisper model pre-download failed, will retry at runtime"

# Set environment variables
ENV PYTHONPATH=/app
ENV LOG_LEVEL=INFO
ENV LOG_FILE=/app/logs/transcription.log
ENV DEFAULT_TRANSCRIPTION_PROVIDER=whisper_local
ENV WHISPER_MODEL_SIZE=base

# Additional environment variables to prevent PyTorch issues
ENV PYTORCH_DISABLE_CUDNN_WARNINGS=1
ENV OMP_NUM_THREADS=1
ENV MKL_NUM_THREADS=1
ENV OPENBLAS_NUM_THREADS=1
ENV VECLIB_MAXIMUM_THREADS=1
ENV NUMEXPR_NUM_THREADS=1
ENV TORCH_HOME=/app/.cache/torch

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