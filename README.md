# Meeting Transcription Agent MCP Server

A Python MCP (Model Context Protocol) server that provides real-time meeting transcription capabilities with audio capture from user-selected microphones and speakers. This server runs behind a Docker MCP Gateway and integrates with various transcription services.

## Features

- **Real-time Audio Capture**: Capture audio from user-selected microphones and speakers
- **Local CPU-only Transcription**: Uses local Whisper models without requiring external APIs
- **Ollama Post-Processing**: Enhances transcripts using your self-hosted Ollama instance
- **Session Management**: Handle multiple concurrent recording sessions
- **Audio Device Discovery**: List and select from available audio input/output devices
- **Docker Integration**: Runs seamlessly behind Docker MCP Gateway
- **Flexible Configuration**: Environment-based configuration with sensible defaults
- **Export Capabilities**: Export transcripts in JSON, TXT, and SRT formats

## Architecture

```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│   MCP Client    │◄──►│ External MCP    │◄──►│ Transcription Agent  │
│                 │    │ Gateway         │    │     (Docker)         │
└─────────────────┘    └─────────────────┘    └──────────────────────┘
                                                          │
                                               ┌──────────▼──────────┐
                                               │  Audio Capture      │
                                               │  - PyAudio          │
                                               │  - Device Discovery │
                                               └──────────┬──────────┘
                                                          │
                                               ┌──────────▼──────────┐
                                               │  Transcription      │
                                               │  - Local Whisper    │
                                               │  - Ollama Enhanced  │
                                               │  - Mock Provider    │
                                               └─────────────────────┘
```

## Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for local development)
- Audio devices (microphone/speakers) connected to the host system

### 1. Clone and Setup

```bash
cd ~/source/meeting-transcription-agent/
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env file with your API keys and preferences
```

### 3. Configure External MCP Gateway

Edit `.env` to point to your existing MCP Gateway:
```bash
# Set your existing MCP Gateway URL
MCP_GATEWAY_URL=http://your-gateway-ip:8080
```

### 4. Use Pre-built Image from GHCR

The Docker image is automatically built and published to GitHub Container Registry:

```bash
# Pull the latest image
docker pull ghcr.io/your-username/meeting-transcription-agent:latest

# Or use a specific version
docker pull ghcr.io/your-username/meeting-transcription-agent:v1.0.0
```

### 5. Start the Transcription Agent

```bash
# Start using pre-built image (default)
docker-compose up -d

# View logs
docker-compose logs -f meeting-transcription

# Stop services
docker-compose down
```

#### Alternative: Build Locally

If you prefer to build the image locally:

```bash
# Edit docker-compose.yml to uncomment the build section
# Then start with local build
docker-compose up -d --build
```

### 4. Alternative: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server directly
python -m src.main
```

## Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WHISPER_MODEL_SIZE` | Local Whisper model size (tiny/base/small/medium/large) | base | No |
| `OLLAMA_URL` | Ollama server URL for transcript post-processing | - | No |
| `OLLAMA_MODEL` | Ollama model name for post-processing | llama2 | No |
| `DEFAULT_SAMPLE_RATE` | Audio sample rate (Hz) | 16000 | No |
| `DEFAULT_CHANNELS` | Audio channels | 1 | No |
| `DEFAULT_CHUNK_DURATION` | Audio chunk duration (seconds) | 30 | No |
| `MAX_CONCURRENT_SESSIONS` | Maximum concurrent sessions | 5 | No |
| `SESSION_TIMEOUT` | Session timeout (seconds) | 3600 | No |
| `DEFAULT_TRANSCRIPTION_PROVIDER` | Default provider (whisper_local/mock) | whisper_local | No |
| `LOG_LEVEL` | Logging level | INFO | No |

All transcription is performed locally without requiring external API keys.

### Audio Device Setup

The server automatically discovers available audio devices. For Docker deployment:

- **Linux**: Audio devices are mounted as volumes (`/dev/snd`)
- **macOS**: May require additional Docker Desktop configuration
- **Windows**: May require PulseAudio or similar audio routing

## API Reference

### Available Tools

#### `start_recording`
Start a new meeting recording session.

**Parameters:**
- `session_id` (string, required): Unique identifier for the session
- `microphone_device` (string, required): Microphone device name or ID
- `speaker_device` (string, optional): Speaker device name or ID
- `sample_rate` (integer, optional): Audio sample rate (default: 16000)
- `channels` (integer, optional): Number of audio channels (default: 1)
- `chunk_duration` (integer, optional): Audio chunk duration in seconds (default: 30)
- `transcription_provider` (string, optional): Override default provider (whisper_local/mock)

**Example:**
```json
{
  "session_id": "meeting-2024-01-15-10-30",
  "microphone_device": "USB Microphone",
  "speaker_device": "default",
  "sample_rate": 16000,
  "channels": 1,
  "chunk_duration": 30,
  "transcription_provider": "whisper_local"
}
```

#### `stop_recording`
Stop a recording session and get the final transcript.

**Parameters:**
- `session_id` (string, required): ID of the session to stop

#### `get_session_status`
Get the current status of a recording session.

**Parameters:**
- `session_id` (string, required): ID of the session to check

#### `list_audio_devices`
List all available audio input and output devices.

**Parameters:** None

### Available Resources

#### `meeting://sessions/active`
Lists currently active recording sessions.

#### `meeting://devices/audio`
Lists available audio input and output devices.

## Usage Examples

### Basic Meeting Transcription

1. **List available audio devices:**
```bash
# Using MCP client
mcp call list_audio_devices
```

2. **Start recording with local Whisper:**
```bash
mcp call start_recording '{
  "session_id": "daily-standup-jan-15",
  "microphone_device": "USB Microphone",
  "speaker_device": "default",
  "transcription_provider": "whisper_local"
}'
```

3. **Check session status:**
```bash
mcp call get_session_status '{
  "session_id": "daily-standup-jan-15"
}'
```

4. **Stop recording and get enhanced transcript:**
```bash
mcp call stop_recording '{
  "session_id": "daily-standup-jan-15"
}'
# If Ollama is configured, transcript will be automatically post-processed
```

### Transcription Provider Options

#### Local Whisper (CPU-only, no API keys required)
```bash
# Different model sizes for speed vs accuracy trade-off
mcp call start_recording '{
  "session_id": "meeting-1",
  "microphone_device": "Built-in Microphone",
  "transcription_provider": "whisper_local"
}'
```

#### Mock Provider (for testing)
```bash
mcp call start_recording '{
  "session_id": "test-meeting",
  "microphone_device": "any",
  "transcription_provider": "mock"
}'
```

### Advanced Configuration

For production deployments with specific transcription providers:

```bash
# Set OpenAI API key for Whisper transcription
export OPENAI_API_KEY="your-openai-api-key"
export DEFAULT_TRANSCRIPTION_PROVIDER="openai"

# Start with enhanced configuration
docker-compose up -d
```

## Development

### Project Structure

```
meeting-transcription-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # MCP server entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   └── capture.py          # Audio capture implementation
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── service.py          # Transcription service providers
│   └── config/
│       ├── __init__.py
│       └── settings.py         # Configuration management
├── requirements.txt            # Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-service deployment
├── .env.example               # Environment variables template
└── README.md                  # This file
```

### Adding New Transcription Providers

1. Create a new provider class inheriting from `TranscriptionProvider`
2. Implement the `transcribe_audio` method
3. Register the provider in `TranscriptionService.__init__`

Example:
```python
class CustomTranscriptionProvider(TranscriptionProvider):
    async def transcribe_audio(self, audio_data: bytes, session_config: Dict[str, Any]) -> TranscriptionResult:
        # Your implementation here
        return TranscriptionResult(text="transcribed text", confidence=0.95)
```

### Testing

```bash
# Install test dependencies
pip install pytest pytest-asyncio

# Run tests
pytest tests/

# Run with coverage
pytest --cov=src tests/
```

## Docker Gateway Integration

This MCP server is designed to work with the Docker MCP Gateway. The gateway provides:

- **Protocol Translation**: Converts between different MCP transport protocols
- **Load Balancing**: Distributes requests across multiple server instances
- **Health Monitoring**: Monitors server health and restarts if needed
- **Authentication**: Handles authentication and authorization

### Gateway Configuration

The MCP Gateway automatically discovers and routes to the transcription server. Configuration is handled through environment variables and Docker networking.

## Troubleshooting

### Common Issues

1. **Audio devices not detected:**
   - Ensure audio devices are properly connected
   - Check Docker volume mounts for `/dev/snd`
   - Verify permissions for audio device access

2. **Transcription not working:**
   - Check API keys in environment variables
   - Verify internet connectivity for cloud providers
   - Check logs for detailed error messages

3. **Docker networking issues:**
   - Ensure all services are on the same Docker network
   - Check port conflicts (default: 8080)
   - Verify firewall settings

### Logs and Debugging

```bash
# View server logs
docker-compose logs -f meeting-transcription

# Enable debug logging
export LOG_LEVEL=DEBUG
docker-compose restart meeting-transcription

# Access container for debugging
docker exec -it meeting-transcription-agent bash
```

## Security Considerations

- **API Keys**: Store sensitive API keys in environment variables or Docker secrets
- **Audio Privacy**: Audio data is processed in memory and not stored persistently by default
- **Network Security**: Use HTTPS and proper authentication in production
- **Container Security**: Run containers with non-root users and minimal privileges

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## License

This project is licensed under the MIT License. See LICENSE file for details.

## Support

For issues and questions:
- Check the troubleshooting section above
- Review Docker and MCP Gateway documentation
- Submit issues with detailed logs and configuration