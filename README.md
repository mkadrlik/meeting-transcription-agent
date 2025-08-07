# Meeting Transcription Agent MCP Server

A Python MCP (Model Context Protocol) server that provides real-time meeting transcription capabilities with both direct device access and client-side audio forwarding. This server runs behind a Docker MCP Gateway and integrates with various transcription services.

## Features

- **Dual Audio Capture Modes**:
  - Direct device access for local environments
  - Client-side audio forwarding for containerized deployments
- **Local CPU-only Transcription**: Uses local Whisper models without requiring external APIs
- **Ollama Post-Processing**: Enhances transcripts using your self-hosted Ollama instance
- **Session Management**: Handle multiple concurrent recording sessions
- **Audio Device Discovery**: List and select from available audio input/output devices
- **Client Audio Forwarding**: Receive audio data from web browsers and desktop applications
- **Docker Integration**: Runs seamlessly behind Docker MCP Gateway
- **Flexible Configuration**: Environment-based configuration with sensible defaults
- **Export Capabilities**: Export transcripts in JSON, TXT, and SRT formats

## Architecture

### Client-Side Audio Forwarding (Recommended for Docker)
```
┌─────────────────┐    ┌─────────────────┐    ┌──────────────────────┐
│   MCP Client    │◄──►│ External MCP    │◄──►│ Transcription Agent  │
│ + Audio Capture │    │ Gateway         │    │     (Docker)         │
│   - Microphone  │    │                 │    │                      │
│   - Web Audio   │    │                 │    │                      │
│   - Base64      │    │                 │    │                      │
└─────────────────┘    └─────────────────┘    └──────────────────────┘
         │                                                    │
         │ Audio Chunks                          ┌────────────▼────────────┐
         └──────────────────────────────────────►│ Client Audio Bridge     │
                                                 │ - Receive audio chunks  │
                                                 │ - Session management    │
                                                 │ - Audio reconstruction  │
                                                 └────────────┬────────────┘
                                                              │
                                                 ┌────────────▼────────────┐
                                                 │  Transcription Service  │
                                                 │  - Local Whisper        │
                                                 │  - Ollama Enhanced      │
                                                 │  - Mock Provider        │
                                                 └─────────────────────────┘
```

### Direct Device Access (Legacy)
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
Start a new meeting recording session (direct device access).

**Parameters:**
- `session_id` (string, required): Unique identifier for the session
- `microphone_device` (string, required): Microphone device name or ID
- `speaker_device` (string, required): Speaker device name or ID

**Note:** Audio technical parameters (sample_rate, channels, chunk_duration) are configured via environment variables for consistency.

**Example:**
```json
{
  "session_id": "meeting-2024-01-15-10-30",
  "microphone_device": "USB Microphone",
  "speaker_device": "Built-in Speakers"
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

#### `get_device_selection_options`
Get available audio devices formatted for easy selection before starting recording.

**Parameters:**
- `session_id` (string, required): Session ID for the planned recording

**Returns:** Formatted list of available microphones and speakers with selection examples.

**Example:**
```json
{
  "session_id": "meeting-001"
}
```

**Example Response:**
```json
{
  "session_id": "meeting-001",
  "available_microphones": [
    {
      "id": "USB Microphone",
      "name": "Blue Yeti USB Microphone",
      "description": "USB Audio Device"
    }
  ],
  "available_speakers": [
    {
      "id": "Built-in Speakers",
      "name": "MacBook Pro Speakers",
      "description": "Built-in Audio"
    }
  ],
  "workflow_instructions": {
    "step1": "Choose a microphone from available_microphones list",
    "step2": "Choose a speaker from available_speakers list",
    "step3": "Call start_recording again with both device IDs specified"
  }
}
```

### Client Audio Forwarding Tools

#### `get_audio_instructions`
Get instructions for implementing client-side audio capture.

**Parameters:**
- `instruction_type` (string, optional): Type of instructions ("web_audio" or "desktop", default: "web_audio")

**Example:**
```json
{
  "instruction_type": "web_audio"
}
```

#### `start_client_recording`
Start a recording session that receives audio from the client.

**Parameters:**
- `session_id` (string, required): Unique identifier for the session
- `sample_rate` (integer, optional): Audio sample rate (default: 16000)
- `channels` (integer, optional): Number of audio channels (default: 1)
- `chunk_duration` (integer, optional): Audio chunk duration in seconds (default: 5)

**Example:**
```json
{
  "session_id": "client-meeting-001",
  "sample_rate": 16000,
  "channels": 1,
  "chunk_duration": 5
}
```

#### `send_audio_chunk`
Send an audio chunk from the client to the server.

**Parameters:**
- `session_id` (string, required): ID of the recording session
- `audio_data` (string, required): Base64-encoded audio data
- `metadata` (object, optional): Metadata about the audio chunk

**Example:**
```json
{
  "session_id": "client-meeting-001",
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=",
  "metadata": {
    "timestamp": 1705123456.789,
    "format": "wav",
    "size": 32000
  }
}
```

#### `stop_client_recording`
Stop client recording and get the final transcript.

**Parameters:**
- `session_id` (string, required): ID of the session to stop

#### `get_client_session_status`
Get the current status of a client recording session.

**Parameters:**
- `session_id` (string, required): ID of the session to check

### Export Tools

#### `export_transcript`
Export a session transcript to a file.

**Parameters:**
- `session_id` (string, required): ID of the session to export
- `format` (string, optional): Export format ("json", "txt", or "srt", default: "json")
- `file_path` (string, optional): Custom file path (if not provided, auto-generated)

**Example:**
```json
{
  "session_id": "meeting-2024-01-15-10-30",
  "format": "txt",
  "file_path": "/tmp/transcripts/meeting_summary.txt"
}
```

#### `list_exported_transcripts`
List all exported transcript files.

**Parameters:**
- `exports_dir` (string, optional): Directory to scan (default: "/tmp/transcripts")

### Available Resources

#### `meeting://sessions/active`
Lists currently active recording sessions.

#### `meeting://devices/audio`
Lists available audio input and output devices.

## Usage Examples

### Basic Meeting Transcription

#### Option 1: Guided Device Selection (Recommended)

1. **Get device selection options:**
```bash
mcp call get_device_selection_options '{
  "session_id": "daily-standup-jan-15"
}'
```

2. **Start recording with selected devices:**
```bash
# Use the device IDs from the previous response
mcp call start_recording '{
  "session_id": "daily-standup-jan-15",
  "microphone_device": "USB Microphone",
  "speaker_device": "Built-in Speakers"
}'
```

#### Option 2: Direct Device Specification

1. **List available audio devices:**
```bash
mcp call list_audio_devices
```

2. **Start recording with known device names:**
```bash
mcp call start_recording '{
  "session_id": "daily-standup-jan-15",
  "microphone_device": "USB Microphone",
  "speaker_device": "Built-in Speakers"
}'
```

#### Common Workflow Steps

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

5. **Export transcript to file:**
```bash
mcp call export_transcript '{
  "session_id": "daily-standup-jan-15",
  "format": "txt"
}'
```

6. **List exported transcripts:**
```bash
mcp call list_exported_transcripts
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

### Client Audio Forwarding (Recommended for Docker)

For containerized deployments where direct audio device access is limited:

1. **Get client implementation instructions:**
```bash
mcp call get_audio_instructions '{
  "instruction_type": "web_audio"
}'
```

2. **Start client recording session:**
```bash
mcp call start_client_recording '{
  "session_id": "client-meeting-001",
  "sample_rate": 16000,
  "channels": 1,
  "chunk_duration": 5
}'
```

3. **Send audio chunks from client:**
```bash
# Client captures audio and sends base64-encoded chunks
mcp call send_audio_chunk '{
  "session_id": "client-meeting-001",
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA=",
  "metadata": {
    "timestamp": 1705123456.789,
    "format": "wav",
    "size": 32000
  }
}'
```

4. **Stop and get transcript:**
```bash
mcp call stop_client_recording '{
  "session_id": "client-meeting-001"
}'
```

**For detailed client implementation examples**, see [`CLIENT_AUDIO_GUIDE.md`](./CLIENT_AUDIO_GUIDE.md) which includes:
- Complete JavaScript web browser implementation
- Python desktop application example
- Audio format requirements and best practices

### Advanced Configuration

For production deployments with specific transcription providers:

```bash
# Configure Whisper model size for performance/accuracy trade-off
export WHISPER_MODEL_SIZE="small"

# Configure Ollama for transcript enhancement
export OLLAMA_URL="http://your-ollama-server:11434"
export OLLAMA_MODEL="llama2"

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