# Fast Whisper MCP Server

A simplified Python MCP (Model Context Protocol) server for high-performance audio transcription using faster-whisper. Designed for speed, simplicity, and developer experience.

## 🚀 Key Features

- **Fast Transcription**: Uses faster-whisper for 4x speed improvement over OpenAI Whisper
- **Simple API**: Just 6 MCP tools for complete transcription workflow
- **File Output**: Automatically saves transcriptions to `/app/data/transcriptions/`
- **Client Audio Support**: Accepts base64-encoded audio from any client
- **Minimal Dependencies**: Streamlined for fast deployment and reliability

## 🏗️ Simple Workflow

1. **Start Session**: `start_session(session_id)`
2. **Send Audio**: `add_audio_chunk(session_id, base64_audio)`
3. **Transcribe**: `transcribe_session(session_id)` → saves to `/app/data/transcriptions/`
4. **Retrieve**: `get_transcription(filename)` or `list_transcriptions()`
## 🚀 Quick Start

```bash
# Start the server
docker compose up -d

# View logs
docker compose logs -f

# Test the service
docker compose exec fast-whisper-mcp python scripts/test.py
```

## ⚙️ Configuration

| Variable | Description | Default |
|----------|-------------|---------|
| `WHISPER_MODEL_SIZE` | Model size (tiny/base/small/medium/large) | base |
| `LOG_LEVEL` | Logging level | INFO |

## 📁 Output

Transcriptions are automatically saved to:
- **Container**: `/app/data/transcriptions/`
- **Host**: `/DATA/san-raid5/AppData/meeting-transcription-agent/data/transcriptions/`

Each transcription includes:
- Full text
- Timestamped segments
- Language detection
- Confidence scores
- Word count and duration
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