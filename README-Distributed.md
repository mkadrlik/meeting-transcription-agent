# Meeting Transcription Agent - Distributed Setup

This guide explains how to set up the Meeting Transcription Agent in a distributed configuration where audio is captured on one system and transcribed on another (MCP server host).

## Architecture Overview

```
[Client System]                    [MCP Server Host]
┌─────────────────┐               ┌─────────────────┐
│   Microphone    │               │                 │
│   Speaker       │    TCP/IP     │  Whisper AI     │
│   Audio Client  │ ──────────►   │  Transcription  │
│                 │    Stream     │  Server         │
└─────────────────┘               └─────────────────┘
```

## Deployment Options

### Option 1: Docker Compose (Same Network)
Use when both client and server are on the same network.

**On MCP Server Host:**
```bash
# Start the transcription server
docker-compose -f docker-compose.distributed.yml up transcription-server
```

**On Client System:**
```bash
# Start the audio client (pointing to server IP)
docker run --rm -it --device /dev/snd:/dev/snd \
  meeting-transcription-client \
  dotnet MeetingTranscriptionAgent.dll client --host <SERVER_IP> --port 8888
```

### Option 2: Separate Deployment

**Step 1: Build Images**
```bash
# Build server image
docker build -f Dockerfile.server -t meeting-transcription-server .

# Build client image  
docker build -f Dockerfile.client -t meeting-transcription-client .
```

**Step 2: Deploy Server (MCP Server Host)**
```bash
# Run transcription server
docker run -d --name transcription-server \
  -p 8888:8888 \
  -v $(pwd)/transcriptions:/app/transcriptions \
  meeting-transcription-server
```

**Step 3: Deploy Client (User's System)**
```bash
# Run audio client
docker run --rm -it --name audio-client \
  --device /dev/snd:/dev/snd \
  meeting-transcription-client \
  dotnet MeetingTranscriptionAgent.dll client --host <SERVER_IP> --port 8888
```

## Usage Modes

### 1. Standalone Mode (Original)
Single system with local microphone and transcription:
```bash
docker run --rm -it --device /dev/snd:/dev/snd \
  meeting-transcription-agent \
  dotnet MeetingTranscriptionAgent.dll standalone
```

### 2. Client Mode (Audio Capture)
Captures audio and streams to remote server:
```bash
# Interactive mode
docker run --rm -it --device /dev/snd:/dev/snd \
  meeting-transcription-client

# Direct mode
docker run --rm -it --device /dev/snd:/dev/snd \
  meeting-transcription-client \
  dotnet MeetingTranscriptionAgent.dll client --host <SERVER_IP> --port 8888
```

### 3. Server Mode (Transcription Processing)
Receives audio streams and performs transcription:
```bash
# Interactive mode
docker run --rm -it -p 8888:8888 \
  -v $(pwd)/transcriptions:/app/transcriptions \
  meeting-transcription-server

# Direct mode
docker run --rm -it -p 8888:8888 \
  -v $(pwd)/transcriptions:/app/transcriptions \
  meeting-transcription-server \
  dotnet MeetingTranscriptionAgent.dll server --port 8888
```

## Network Configuration

### Firewall Rules
Ensure the MCP server host allows incoming connections on port 8888:
```bash
# Ubuntu/Debian
sudo ufw allow 8888

# CentOS/RHEL
sudo firewall-cmd --add-port=8888/tcp --permanent
sudo firewall-cmd --reload
```

### Port Configuration
- **Default Port**: 8888
- **Protocol**: TCP
- **Direction**: Client → Server

## Audio Support

### Supported Audio Devices
The client automatically detects and tries these audio inputs:
1. Blue Microphones USB Audio (`hw:2,0`)
2. Depstech webcam MIC (`hw:3,0`)
3. HDA Analog (`hw:1,0`)
4. DMIC (`hw:1,6`)
5. ALSA default
6. PulseAudio default

### Troubleshooting Audio
```bash
# List available audio devices
arecord -l

# Test audio capture
arecord -f cd -t wav -d 10 test.wav

# Check Docker audio access
docker run --rm --device /dev/snd:/dev/snd \
  meeting-transcription-client \
  arecord -l
```

## File Locations

### Transcription Files
- **Local**: `./transcriptions/meeting_transcription_YYYYMMDD_HHMMSS.txt`
- **Server**: `./transcriptions/meeting_transcription_<CLIENT_ID>_YYYYMMDD.txt`

### Configuration Files
- [`Dockerfile.client`](Dockerfile.client) - Client container
- [`Dockerfile.server`](Dockerfile.server) - Server container  
- [`docker-compose.distributed.yml`](docker-compose.distributed.yml) - Distributed setup

## Security Considerations

### Network Security
- Audio data is transmitted unencrypted over TCP
- Consider VPN for sensitive communications
- Limit server access to trusted networks

### Audio Privacy
- Audio is processed in real-time (not stored)
- Only transcription text is saved to files
- Client controls when to start/stop streaming

## Performance Considerations

### Bandwidth Requirements
- **Audio Stream**: ~32 kbps (16kHz, 16-bit mono)
- **Network Latency**: <100ms recommended
- **Processing Delay**: ~3-5 seconds per audio chunk

### Hardware Requirements
- **Client**: Minimal (audio capture only)
- **Server**: CPU-intensive for Whisper AI processing
- **Memory**: 2GB+ recommended for Whisper model

## Troubleshooting

### Common Issues

**1. Connection Refused**
```bash
# Check server is running
docker ps | grep transcription-server

# Check network connectivity
telnet <SERVER_IP> 8888
```

**2. No Audio Detected**
```bash
# Verify audio devices
ls -la /dev/snd/

# Check permissions
groups $(whoami) | grep audio
```

**3. Transcription Not Working**
- Server logs: `docker logs transcription-server`
- Client logs: Check console output
- Network: Verify port 8888 is open

### Log Analysis
```bash
# View server logs
docker logs -f transcription-server

# View client logs (run in foreground)
docker run --rm -it meeting-transcription-client [args]
```

## Advanced Configuration

### Custom Server Port
```bash
# Server
docker run -p 9999:9999 meeting-transcription-server \
  dotnet MeetingTranscriptionAgent.dll server --port 9999

# Client
docker run meeting-transcription-client \
  dotnet MeetingTranscriptionAgent.dll client --host <SERVER_IP> --port 9999
```

### Multiple Clients
The server supports multiple simultaneous client connections:
- Each client gets a unique session ID
- Transcriptions are saved separately per client
- No limit on concurrent connections (resource dependent)

## Integration with MCP

The transcription server can be integrated with MCP servers by:
1. Running the transcription server on the same host as your MCP server
2. Configuring clients on remote systems to stream audio
3. Using the transcription files as input for MCP tool processing
4. Setting up webhooks or file watchers for real-time processing

This enables remote audio transcription capabilities for any MCP-based application.