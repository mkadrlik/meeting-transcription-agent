# Meeting Transcription Agent MCP Server

A Python MCP (Model Context Protocol) server that provides real-time meeting transcription capabilities with **DUAL audio capture** for Bluetooth headphones. This server runs behind a Docker MCP Gateway and integrates with various transcription services, featuring a complete host-container audio solution.

## 🎤🔊 Key Features

- **DUAL Audio Capture**: Captures both microphone (your voice) AND speaker output (other participants via Bluetooth)
- **Docker Audio Solution**: Bypass container audio limitations with host-side capture + container-side processing
- **Local CPU-only Transcription**: Uses local Whisper models without requiring external APIs
- **Ollama Post-Processing**: Enhances transcripts using your self-hosted Ollama instance
- **Session Management**: Handle multiple concurrent recording sessions
- **Audio Device Discovery**: List and select from available audio input/output devices
- **Client Audio Forwarding**: Receive audio data from web browsers and desktop applications
- **Docker Integration**: Runs seamlessly behind Docker MCP Gateway
- **Flexible Configuration**: Environment-based configuration with sensible defaults
- **Export Capabilities**: Export transcripts in JSON, TXT, and SRT formats

## 🏗️ Architecture

### Dual Audio Capture Architecture (Recommended for Bluetooth Headphones)

The system uses a **two-part audio architecture** to solve Docker's audio limitations while capturing both sides of conversations:

```
┌─────────────────────┐    HTTP/MCP     ┌──────────────────────────┐
│   HOST MACHINE      │    Request      │    DOCKER CONTAINER      │
│                     │ ──────────────> │                          │
│ src/audio/host_bridge.py│             │ client_bridge.py         │
│   ↑                 │                 │   ↓                      │
│ 🎤 PyAudio (mic)    │                 │ MCP Server Tools         │
│ 🔊 Monitor (speaker)│                 │   ↓                      │
│   ↓                 │                 │ Transcription Service    │
│ Audio Mixing        │                 │   ↓                      │
│   ↓                 │ <────────────── │ Whisper AI Processing    │
│ Base64 WAV          │    Transcript   │                          │
└─────────────────────┘                 └──────────────────────────┘
```

### Two-Part Solution for Docker Audio

The audio system uses **TWO complementary components** to work around Docker's audio limitations:

#### 1. **`src/audio/client_bridge.py`** (SERVER-SIDE) 
- ✅ **Runs INSIDE Docker container**
- ✅ **Part of the MCP server**
- ✅ **Receives audio data** from clients via MCP tools
- ✅ **Manages audio buffers** and session state
- ✅ **Processes incoming base64-encoded audio**

#### 2. **`src/audio/host_bridge.py`** (CLIENT-SIDE)
- ✅ **Runs ON HOST machine** (outside Docker)
- ✅ **Captures real dual audio** using PyAudio (mic + speaker monitor)
- ✅ **Mixes audio sources** intelligently (60% mic, 40% speaker)
- ✅ **Converts audio to base64 WAV format**
- ✅ **Sends audio TO the Docker container** via HTTP

### Data Flow:
1. **Host microphone** → `src/audio/host_bridge.py` (PyAudio capture)
2. **Speaker monitor** → Host audio bridge (captures Bluetooth output)
3. **Audio mixing** → Combines mic (60%) + speaker (40%) streams
4. **Base64 WAV** → HTTP POST to Docker container MCP gateway
5. **MCP tools** → `client_bridge.py` (receives/stores audio)
6. **Audio buffer** → Transcription service
7. **Whisper AI** → Text transcript
8. **HTTP response** → Back to host with results

### Why Both Components Are Needed:

#### **Without `client_bridge.py`:**
- ❌ Docker container has no way to receive audio data
- ❌ No MCP tools for audio forwarding
- ❌ No session management for incoming audio

#### **Without `src/audio/host_bridge.py`:**
- ❌ Docker can't access host microphone directly
- ❌ ALSA errors in containerized environments
- ❌ No way to capture real audio from Bluetooth devices

#### **With BOTH Together:**
- ✅ Host captures dual audio (mic + Bluetooth speaker output)
- ✅ Docker processes audio with Whisper AI
- ✅ Complete client-server audio solution
- ✅ Bypasses Docker audio limitations

## 🚀 Quick Start

### Prerequisites

- Docker and Docker Compose
- Python 3.11+ (for host-side audio capture)
- Audio devices (microphone/Bluetooth headphones) connected to the host system

### 1. Clone and Setup

```bash
cd ~/source/meeting-transcription-agent/
```

### 2. Configure Environment Variables

```bash
cp .env.example .env
# Edit .env file with your API keys and preferences
```

### 3. Start Complete Recording Solution

The **simplest way** to start recording with dual audio capture:

```bash
# Install host requirements and start everything
./start_recording.sh
```

This automatically:
1. Installs host-side Python dependencies (`pyaudio`, `numpy`, `requests`)
2. Starts Docker MCP server container
3. Launches dual audio bridge for microphone + Bluetooth speaker capture
4. Begins live meeting transcription

### 4. Alternative: Manual Docker Setup

```bash
# Start just the Docker container
docker-compose up -d

# View logs
docker-compose logs -f meeting-transcription

# Stop services
docker-compose down
```

### 5. Alternative: Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Run the MCP server directly
python -m src.main
```

## 📱 Dual Audio Capture Details

### Microphone + Bluetooth Speaker Capture

The host audio bridge automatically:

1. **Detects your microphone device** (captures your voice)
2. **Searches for speaker monitor devices** (captures other participants via Bluetooth)
3. **Mixes both audio streams** intelligently (60% mic, 40% speaker)
4. **Sends combined audio** to Docker container for Whisper AI processing

### Supported Audio Configurations:

- **Bluetooth Headphones**: ✅ Captures both microphone input and audio output
- **USB Headsets**: ✅ Full dual audio capture
- **Built-in Audio**: ✅ Microphone + speaker monitor (if available)
- **Microphone Only**: ✅ Graceful fallback if speaker monitor unavailable

### Audio Device Discovery:

The system shows you exactly what it finds:
```
🔍 Available audio devices:
  🎤 Input 0: Blue Yeti USB Microphone
  🎤 Input 1: Built-in Microphone
  🔊 Output 0: AirPods Pro (Bluetooth)
  🔊 Output 1: Built-in Speakers

📻 Found monitor device 2: Built-in Output Monitor
✅ Speaker monitor enabled on device 2
```

## ⚙️ Configuration

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
| `DISABLE_AUDIO_CAPTURE` | Disable direct audio in container | true | No |

All transcription is performed locally without requiring external API keys.

### Audio Device Setup

#### For Docker Deployment (Recommended):
- **Host audio capture**: Handles all audio device access via `host_bridge.py`
- **Container processing**: Handles AI transcription via Whisper
- **Linux**: Works out of the box
- **macOS**: Compatible with built-in and Bluetooth audio
- **Windows**: Compatible with standard audio devices

#### For Direct Device Access (Legacy):
- **Linux**: Audio devices mounted as volumes (`/dev/snd`)
- **macOS**: May require additional Docker Desktop configuration
- **Windows**: May require PulseAudio or similar audio routing

## 🛠️ API Reference

### Available Tools

#### `start_recording`
Start a new meeting recording session (direct device access).

**Parameters:**
- `session_id` (string, required): Unique identifier for the session
- `microphone_device` (string, required): Microphone device name or ID
- `speaker_device` (string, required): Speaker device name or ID

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

### Client Audio Forwarding Tools (For Host Bridge)

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
    "size": 32000,
    "sources": "microphone+speaker"
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

#### `meeting://devices/audio`
Lists available audio input and output devices.

## 📝 Usage Examples

### Basic Meeting Transcription with Dual Audio

#### Option 1: Simple One-Command Start (Recommended)

```bash
# Start complete dual audio recording solution
./start_recording.sh

# The script will:
# 1. Install required host dependencies
# 2. Start Docker MCP server
# 3. Launch dual audio bridge
# 4. Show you available devices
# 5. Begin recording both mic + speaker
```

#### Option 2: Manual MCP Tools

1. **List available audio devices:**
```bash
mcp call list_audio_devices
```

2. **Start recording with device selection:**
```bash
mcp call start_recording '{
  "session_id": "daily-standup-jan-15",
  "microphone_device": "USB Microphone",
  "speaker_device": "AirPods Pro"
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
```

### Advanced Client Implementation Examples

#### Web Browser Implementation

```javascript
class DualAudioRecorder {
    constructor(mcpClient, sessionId) {
        this.mcpClient = mcpClient;
        this.sessionId = sessionId;
        this.mediaRecorder = null;
        this.stream = null;
        this.isRecording = false;
    }

    async startRecording() {
        try {
            // Start MCP recording session
            const sessionResult = await this.mcpClient.callTool('start_client_recording', {
                session_id: this.sessionId,
                sample_rate: 16000,
                channels: 1,
                chunk_duration: 5
            });
            
            console.log('MCP session started:', sessionResult);

            // Request microphone access with enhanced settings
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                    autoGainControl: true
                }
            });

            // Create MediaRecorder with optimal settings
            this.mediaRecorder = new MediaRecorder(this.stream, {
                mimeType: 'audio/webm;codecs=opus'
            });

            this.mediaRecorder.ondataavailable = async (event) => {
                if (event.data.size > 0) {
                    await this.sendAudioChunk(event.data);
                }
            };

            // Start recording with 5-second chunks
            this.mediaRecorder.start(5000);
            this.isRecording = true;

            console.log('Dual audio recording started');
        } catch (error) {
            console.error('Failed to start recording:', error);
            throw error;
        }
    }

    async sendAudioChunk(audioBlob) {
        try {
            // Convert blob to base64
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));

            // Send to MCP server with metadata
            const result = await this.mcpClient.callTool('send_audio_chunk', {
                session_id: this.sessionId,
                audio_data: base64,
                metadata: {
                    timestamp: Date.now(),
                    format: 'webm',
                    size: arrayBuffer.byteLength,
                    sources: 'microphone'
                }
            });

            console.log('Audio chunk sent:', result);
        } catch (error) {
            console.error('Failed to send audio chunk:', error);
        }
    }

    async stopRecording() {
        try {
            if (this.mediaRecorder && this.isRecording) {
                this.mediaRecorder.stop();
            }

            if (this.stream) {
                this.stream.getTracks().forEach(track => track.stop());
            }

            // Stop MCP recording session and get transcript
            const result = await this.mcpClient.callTool('stop_client_recording', {
                session_id: this.sessionId
            });

            this.isRecording = false;
            console.log('Recording stopped:', result);
            return result;
        } catch (error) {
            console.error('Failed to stop recording:', error);
            throw error;
        }
    }
}

// Usage example
async function startMeetingTranscription() {
    const sessionId = `meeting-${Date.now()}`;
    const recorder = new DualAudioRecorder(mcpClient, sessionId);
    
    try {
        await recorder.startRecording();
        
        // Record until user stops
        document.getElementById('stopButton').addEventListener('click', async () => {
            const result = await recorder.stopRecording();
            console.log('Final transcript:', result.transcript);
            document.getElementById('transcript').textContent = result.transcript.full_text;
        });
        
    } catch (error) {
        console.error('Recording failed:', error);
    }
}
```

#### Python Desktop Implementation

```python
import asyncio
import base64
import pyaudio
import wave
import io
import time
from mcp_client import MCPClient

class DesktopDualAudioRecorder:
    def __init__(self, mcp_client, session_id):
        self.mcp_client = mcp_client
        self.session_id = session_id
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        
        # Audio settings optimized for dual capture
        self.sample_rate = 16000
        self.channels = 1
        self.chunk_size = 1024
        self.format = pyaudio.paInt16

    async def start_recording(self):
        try:
            # Start MCP recording session
            session_result = await self.mcp_client.call_tool('start_client_recording', {
                'session_id': self.session_id,
                'sample_rate': self.sample_rate,
                'channels': self.channels,
                'chunk_duration': 5
            })
            
            print(f"MCP session started: {session_result}")

            # Open audio stream with enhanced settings
            self.stream = self.audio.open(
                format=self.format,
                channels=self.channels,
                rate=self.sample_rate,
                input=True,
                frames_per_buffer=self.chunk_size
            )

            self.is_recording = True
            
            # Start recording loop
            asyncio.create_task(self._recording_loop())
            print("Dual audio recording started")
            
        except Exception as e:
            print(f"Failed to start recording: {e}")
            raise

    async def _recording_loop(self):
        chunk_duration = 5  # seconds
        frames_per_chunk = int(self.sample_rate * chunk_duration)
        
        while self.is_recording:
            try:
                # Record audio chunk
                frames = []
                for _ in range(0, frames_per_chunk, self.chunk_size):
                    if not self.is_recording:
                        break
                    data = self.stream.read(self.chunk_size)
                    frames.append(data)
                
                if frames:
                    # Convert to WAV format
                    audio_data = b''.join(frames)
                    wav_data = self._create_wav_bytes(audio_data)
                    
                    # Encode to base64
                    base64_data = base64.b64encode(wav_data).decode('utf-8')
                    
                    # Send to MCP server with enhanced metadata
                    result = await self.mcp_client.call_tool('send_audio_chunk', {
                        'session_id': self.session_id,
                        'audio_data': base64_data,
                        'metadata': {
                            'timestamp': time.time(),
                            'format': 'wav',
                            'size': len(wav_data),
                            'sources': 'microphone',
                            'quality': 'enhanced'
                        }
                    })
                    
                    print(f"Audio chunk sent: {result}")
                    
            except Exception as e:
                print(f"Error in recording loop: {e}")
                break

    def _create_wav_bytes(self, audio_data):
        """Convert raw audio data to WAV format"""
        wav_buffer = io.BytesIO()
        
        with wave.open(wav_buffer, 'wb') as wav_file:
            wav_file.setnchannels(self.channels)
            wav_file.setsampwidth(self.audio.get_sample_size(self.format))
            wav_file.setframerate(self.sample_rate)
            wav_file.writeframes(audio_data)
        
        return wav_buffer.getvalue()

    async def stop_recording(self):
        try:
            self.is_recording = False
            
            if self.stream:
                self.stream.stop_stream()
                self.stream.close()
            
            # Stop MCP recording session and get transcript
            result = await self.mcp_client.call_tool('stop_client_recording', {
                'session_id': self.session_id
            })
            
            print(f"Recording stopped: {result}")
            return result
            
        except Exception as e:
            print(f"Failed to stop recording: {e}")
            raise
        finally:
            self.audio.terminate()

# Usage example
async def main():
    mcp_client = MCPClient("stdio://meeting-transcription-agent")
    session_id = f"meeting-{int(time.time())}"
    
    recorder = DesktopDualAudioRecorder(mcp_client, session_id)
    
    try:
        await recorder.start_recording()
        
        # Record for duration or until interrupted
        print("Recording... Press Ctrl+C to stop")
        await asyncio.sleep(30)  # Record for 30 seconds
        
        result = await recorder.stop_recording()
        print(f"Final transcript: {result['transcript']['full_text']}")
        
    except KeyboardInterrupt:
        print("Recording stopped by user")
        await recorder.stop_recording()
    except Exception as e:
        print(f"Recording failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## 🐳 Docker Audio Solutions

### The Docker Audio Problem

Docker containers run in isolation from the host audio system, causing:
- **ALSA errors**: "Cannot connect to server socket"
- **Audio device access issues**: Devices not visible in container
- **Permission problems**: User ID and audio group mismatches
- **Complex mounting**: `/dev/snd` volume mounts often fail

### ✅ Our Solution: Host Bridge Architecture

Instead of fighting Docker audio access, we use **client-side audio forwarding**:

```bash
# This works reliably across all platforms
./start_recording.sh
```

**Benefits:**
- ✅ Direct microphone + speaker access on host
- ✅ Real Whisper AI transcription in container
- ✅ No Docker audio complexity
- ✅ Works with Bluetooth devices
- ✅ Immediate, reliable results

### Alternative Docker Audio Solutions (Advanced)

If you need container-native audio:

#### Option A: Host Network Mode
```yaml
# In docker-compose.yml
network_mode: "host"
```

#### Option B: PulseAudio Forwarding
```bash
# On host, allow Docker access
pactl load-module module-native-protocol-tcp auth-anonymous=1

# Then run container with:
environment:
  - PULSE_SERVER=tcp:host.docker.internal:4713
```

#### Option C: X11 Audio Forwarding
```yaml
volumes:
  - /tmp/.X11-unix:/tmp/.X11-unix:rw
  - $HOME/.Xauthority:/home/user/.Xauthority:rw
environment:
  - DISPLAY=$DISPLAY
```

### Recommendation

**Use the host bridge approach** (`./start_recording.sh`) for:
1. **Immediate meeting recording needs**
2. **Bluetooth headphone compatibility**
3. **Reliable cross-platform operation**
4. **Dual audio capture (mic + speaker)**

The Docker container excels at **server-side processing** where audio data is sent TO it rather than captured BY it.

## 🔧 Development

### Project Structure

```
meeting-transcription-agent/
├── src/
│   ├── __init__.py
│   ├── main.py                 # MCP server entry point
│   ├── audio/
│   │   ├── __init__.py
│   │   ├── capture.py          # Direct audio capture (legacy)
│   │   ├── host_bridge.py      # Host-side dual audio capture
│   │   └── client_bridge.py    # Container-side audio receiver
│   ├── transcription/
│   │   ├── __init__.py
│   │   └── service.py          # Whisper transcription providers
│   └── config/
│       ├── __init__.py
│       └── settings.py         # Configuration management
├── requirements.txt            # Container Python dependencies
├── requirements-host.txt       # Host-side Python dependencies
├── Dockerfile                  # Container configuration
├── docker-compose.yml          # Multi-service deployment
├── start_recording.sh          # Complete recording solution
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

#### 1. Audio devices not detected:
```bash
# Check if devices are visible
./start_recording.sh

# Should show:
# 🔍 Available audio devices:
#   🎤 Input 0: Your Microphone
#   🔊 Output 0: Your Bluetooth Headphones
```

**Solutions:**
- Ensure Bluetooth headphones are connected and working
- Check audio devices are not exclusively used by other apps
- Restart audio services: `pulseaudio --kill && pulseaudio --start`

#### 2. Host bridge connection failed:
```bash
# Check if Docker container is running
docker-compose ps

# Should show container as "Up"
```

**Solutions:**
- Ensure Docker container started: `docker-compose up -d`
- Check port conflicts on 8080
- Verify firewall settings allow localhost connections

#### 3. Bluetooth audio not captured:
```bash
# Look for speaker monitor devices
./start_recording.sh

# Should show:
# 📻 Found monitor device X: Built-in Output Monitor
# ✅ Speaker monitor enabled
```

**Solutions:**
- **Linux**: Install `pavucontrol`, enable "Monitor" devices
- **macOS**: Check "System Preferences > Sound > Internal Microphone"
- **Windows**: Enable "Stereo Mix" in sound settings

#### 4. Docker audio errors (ALSA):
```
ALSA lib pcm_dmix.c:1032:(snd_pcm_dmix_open) unable to open slave
```

**Solution:** Use the host bridge (this is expected and solved by our architecture):
```bash
# This bypasses Docker audio completely
./start_recording.sh
```

#### 5. Python dependency issues:
```bash
# Install host requirements manually
pip3 install --user pyaudio numpy requests

# Or using the requirements file
pip3 install --user -r requirements-host.txt
```

### Logs and Debugging

```bash
# View server logs
docker-compose logs -f meeting-transcription

# Enable debug logging
export LOG_LEVEL=DEBUG
./start_recording.sh

# Check audio bridge logs
# (logs appear in terminal when running start_recording.sh)
```

### Platform-Specific Notes

#### **Linux:**
- Works with ALSA, PulseAudio, JACK
- Best speaker monitor support
- May need user in `audio` group: `sudo usermod -a -G audio $USER`

#### **macOS:**
- Works with built-in and USB audio devices
- Bluetooth support via Core Audio
- May need microphone permissions in System Preferences

#### **Windows:**
- Works with DirectSound devices
- May need "Stereo Mix" enabled for speaker capture
- Bluetooth audio depends on driver quality

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
- **Quick Start Issues**: Try `./start_recording.sh` first
- **Audio Problems**: Check the Troubleshooting section above
- **Bluetooth Issues**: Verify devices work with system audio first
- **Docker Problems**: Check container logs with `docker-compose logs -f`
- **Submit Issues**: Include logs, OS version, and audio device details

---

## 📦 Quick Command Reference

```bash
# Complete recording solution (recommended)
./start_recording.sh

# Manual Docker container management
docker-compose up -d          # Start container
docker-compose logs -f        # View logs
docker-compose down          # Stop container

# Host requirements
pip3 install --user -r requirements-host.txt

# Development mode
python -m src.main           # Run MCP server directly
```

This comprehensive solution provides reliable dual audio capture for meeting transcription, especially with Bluetooth headphones and complex audio setups!
