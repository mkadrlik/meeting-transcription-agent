# Meeting Transcription Agent MCP Server

A Python MCP (Model Context Protocol) server that provides real-time meeting transcription capabilities with client-side audio forwarding. This server runs behind a Docker MCP Gateway and integrates with various transcription services.

## 🎤 Key Features

- **Client Audio Forwarding**: Receive audio data from web browsers and desktop applications
- **Docker Integration**: Runs seamlessly behind Docker MCP Gateway
- **Local CPU-only Transcription**: Uses local Whisper models without requiring external APIs
- **Ollama Post-Processing**: Enhances transcripts using your self-hosted Ollama instance
- **Session Management**: Handle multiple concurrent recording sessions
- **Flexible Configuration**: Environment-based configuration with sensible defaults
- **Export Capabilities**: Export transcripts in JSON, TXT, and SRT formats

## 🏗️ Architecture

### Client Audio Forwarding Architecture

The system uses a **client-server architecture** where audio is captured on the client side and forwarded to the server for transcription:

```
┌─────────────────────┐    HTTP/MCP     ┌──────────────────────────┐
│   CLIENT            │    Request      │    DOCKER CONTAINER      │
│                     │ ──────────────> │                          │
│ Audio Capture       │                 │                          │
│   ↓                 │                 │ MCP Server Tools         │
│ Base64 Audio Data   │                 │   ↓                      │
│   ↓                 │ <────────────── │ Transcription Service    │
│                     │    Transcript   │   ↓                      │
└─────────────────────┘                 │ Whisper AI Processing    │
                                        │                          │
                                        └──────────────────────────┘
```

### Data Flow:
1. **Client audio capture** → Web browser or desktop application
2. **Base64 encoding** → Audio data encoded for transmission
3. **MCP tools** → `client_bridge.py` (receives/stores audio)
4. **Audio buffer** → Transcription service
5. **Whisper AI** → Text transcript
6. **HTTP response** → Back to client with results

### Why This Architecture:

#### **Benefits:**
- ✅ Works with any audio source accessible to the client
- ✅ No complex audio device setup on the server
- ✅ Cross-platform compatibility
- ✅ Bypasses Docker audio limitations
- ✅ Secure - audio data is only accessible to the client that sends it

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for client-side audio capture)

### 1. Clone and Setup

```bash
cd ~/source/meeting-transcription-agent/
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env file with your API keys and preferences
```

### 3. Start Server

```bash
# Start just the Docker container
docker-compose up -d

# View logs
docker-compose logs -f meeting-transcription

# Stop services
docker-compose down
```

### 4. Alternative: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server directly
python -m src.main
```

## ⚙️ Configuration

### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `WHISPER_MODEL_SIZE` | Local Whisper model size (tiny/base/small/medium/large) | base | No |

### Whisper Model Initialization

The container automatically downloads and caches the Whisper model during startup:

- **Build Time**: Model is pre-downloaded during Docker image build
- **Runtime**: Entrypoint script verifies model availability before starting MCP server
- **Cache Location**: Models are cached in `/app/.cache/whisper` (mounted to host for persistence)
- **Supported Models**: tiny, base, small, medium, large (base recommended for balance of speed/accuracy)
| `OLLAMA_URL` | Ollama server URL for transcript post-processing | - | No |
| `OLLAMA_MODEL` | Ollama model name for post-processing | llama2 | No |
| `DEFAULT_SAMPLE_RATE` | Audio sample rate (Hz) | 16000 | No |
| `DEFAULT_CHANNELS` | Audio channels | 1 | No |
| `DEFAULT_CHUNK_DURATION` | Audio chunk duration (seconds) | 30 | No |
| `MAX_CONCURRENT_SESSIONS` | Maximum concurrent sessions | 5 | No |
| `SESSION_TIMEOUT` | Session timeout (seconds) | 3600 | No |
| `DEFAULT_TRANSCRIPTION_PROVIDER` | Default provider (whisper_local/mock) | whisper_local | No |
| `LOG_LEVEL` | Logging level | INFO | No |
| `DISABLE_AUDIO_CAPTURE` | Disable direct audio in container | true | No |

All transcription is performed locally without requiring external API keys.

## 🛠️ API Reference

### Available Tools

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

### Export Tools

#### `export_transcript`
Export a session transcript to a file.

**Parameters:**
- `session_id` (string, required): ID of the session to export
- `format` (string, optional): Export format ("json", "txt", or "srt", default: "json")
- `file_path` (string, optional): Custom file path (if not provided, auto-generated)

### Available Resources

#### `meeting://sessions/active`
Lists currently active recording sessions.

## 📝 Usage Examples

### Basic Meeting Transcription with Client Audio

#### Manual MCP Tools

1. **Start client recording:**
```bash
mcp call start_client_recording '{
  "session_id": "daily-standup-jan-15",
  "sample_rate": 16000,
  "channels": 1,
  "chunk_duration": 5
}'
```

2. **Send audio chunks:**
```bash
mcp call send_audio_chunk '{
  "session_id": "daily-standup-jan-15",
  "audio_data": "UklGRiQAAABXQVZFZm10IBAAAAABAAEAgD4AAAB9AAACABAAZGF0YQAAAAA="
}'
```

3. **Stop recording and get enhanced transcript:**
```bash
mcp call stop_client_recording '{
  "session_id": "daily-standup-jan-15"
}'
```

### Advanced Client Implementation

For custom implementations, the system supports client-side audio forwarding:

```javascript
class AudioRecorder {
    constructor(mcpClient, sessionId) {
        this.mcpClient = mcpClient;
        this.sessionId = sessionId;
    }

    async startRecording() {
        // Start MCP recording session
        const result = await this.mcpClient.callTool('start_client_recording', {
            session_id: this.sessionId,
            sample_rate: 16000,
            channels: 1,
            chunk_duration: 5
        });
        
        // Capture audio from microphone
        const stream = await navigator.mediaDevices.getUserMedia({
            audio: {
                sampleRate: 16000,
                channelCount: 1,
                echoCancellation: true,
                noiseSuppression: true
            }
        });

        // Process and send audio chunks to MCP server
        // Implementation details in CLIENT_AUDIO_GUIDE.md
    }
}
```

## 🔧 Development

### Project Structure

```
meeting-transcription-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # MCP server entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   └── client_bridge.py    # Container-side audio receiver
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── service.py          # Whisper transcription providers
│   └── config/
│       ├── __init__.py
│       └── settings.py         # Configuration management
├── requirements.txt            # Container Python dependencies
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

## 🚨 Troubleshooting

### Common Issues

#### 1. Server not starting:
```bash
# Check if Docker container is running
docker-compose ps

# Should show container as "Up"
```

**Solutions:**
- Ensure Docker container started: `docker-compose up -d`
- Check port conflicts
- Verify firewall settings allow localhost connections

#### 2. Python dependency issues:
```bash
# Install dependencies
pip install -r requirements.txt
```

### Logs and Debugging

```bash
# View server logs
docker-compose logs -f meeting-transcription

# Enable debug logging
export LOG_LEVEL=DEBUG
# Then run the server
```

## 🔐 Security Considerations

- **API Keys**: Store sensitive API keys in environment variables or Docker secrets
- **Audio Privacy**: Audio data is processed in memory and not stored persistently by default
- **Network Security**: Use HTTPS and proper authentication in production
- **Container Security**: Run containers with non-root users and minimal privileges
- **Local Processing**: All transcription happens locally - no external API calls required

## 🚀 Docker Gateway Integration

This MCP server is designed to work with the Docker MCP Gateway. The gateway provides:

- **Protocol Translation**: Converts between different MCP transport protocols
- **Load Balancing**: Distributes requests across multiple server instances
- **Health Monitoring**: Monitors server health and restarts if needed
- **Authentication**: Handles authentication and authorization

### Gateway Configuration

The MCP Gateway automatically discovers and routes to the transcription server. Configuration is handled through environment variables and Docker networking.

## 🤝 Contributing
1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Add tests for new functionality
5. Submit a pull request

## 📜 License

This project is licensed under the MIT License. See LICENSE file for details.

## 🆘 Support

For issues and questions:
- **Server Issues**: Check the Troubleshooting section above
- **Docker Problems**: Check container logs with `docker-compose logs -f`
- **Submit Issues**: Include logs, OS version, and audio device details

---

## 📦 Quick Command Reference

```bash
# Manual Docker container management
docker-compose up -d          # Start container
docker-compose logs -f        # View logs
docker-compose down          # Stop container

# Development mode
python -m src.main           # Run MCP server directly
```

This solution provides reliable client-side audio forwarding and transcription for meeting transcription!