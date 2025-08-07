# Client-Side Audio Forwarding Guide

This guide explains how to use the client-side audio forwarding functionality in the Meeting Transcription Agent. This feature allows clients to capture audio locally and send it to the MCP server for transcription, solving the limitation where Docker containers cannot directly access client audio devices.

## Overview

The Meeting Transcription Agent now supports two modes of operation:

1. **Direct Device Access** (legacy): Server directly accesses audio devices (limited in containerized environments)
2. **Client Audio Forwarding** (new): Client captures audio and forwards it to the server

## New Tools for Client Audio Forwarding

### 1. `get_audio_instructions`
Get instructions for implementing client-side audio capture.

**Parameters:**
- `instruction_type` (optional): "web_audio" or "desktop" (default: "web_audio")

**Example Response:**
```json
{
  "type": "web_audio_api",
  "instructions": {
    "1_request_permission": "navigator.mediaDevices.getUserMedia({audio: true})",
    "2_create_recorder": "Use MediaRecorder API or AudioContext",
    "3_capture_chunks": "Record audio in 5-second chunks",
    "4_encode": "Convert to base64 before sending",
    "5_send_via_mcp": "Use send_audio_chunk tool"
  },
  "sample_code": {
    "javascript": "// Complete implementation example"
  },
  "recommended_settings": {
    "chunk_duration_ms": 5000,
    "sample_rate": 16000,
    "channels": 1,
    "bit_depth": 16,
    "format": "wav"
  }
}
```

### 2. `start_client_recording`
Start a recording session that receives audio from the client.

**Parameters:**
- `session_id` (required): Unique identifier for the recording session
- `sample_rate` (optional): Audio sample rate in Hz (default: 16000)
- `channels` (optional): Number of audio channels (default: 1)
- `chunk_duration` (optional): Duration of audio chunks in seconds (default: 5)

**Example Response:**
```json
{
  "session_id": "meeting-2025-01-15-001",
  "status": "waiting_for_audio",
  "message": "Session ready to receive audio from client",
  "instructions": {
    "audio_format": "WAV or raw PCM",
    "encoding": "base64",
    "sample_rate": 16000,
    "channels": 1,
    "chunk_size_ms": 5000
  }
}
```

### 3. `send_audio_chunk`
Send an audio chunk from the client to the server.

**Parameters:**
- `session_id` (required): ID of the recording session
- `audio_data` (required): Base64-encoded audio data
- `metadata` (optional): Metadata about the audio chunk

**Example Response:**
```json
{
  "session_id": "meeting-2025-01-15-001",
  "status": "chunk_received",
  "chunk_number": 5,
  "chunk_size_bytes": 32000,
  "total_chunks": 5,
  "total_duration_seconds": 25.0
}
```

### 4. `stop_client_recording`
Stop client recording and get the final transcript.

**Parameters:**
- `session_id` (required): ID of the session to stop

**Example Response:**
```json
{
  "session_id": "meeting-2025-01-15-001",
  "status": "completed",
  "total_chunks": 12,
  "total_duration_seconds": 60.0,
  "total_audio_bytes": 1920000,
  "session_duration": 62.5,
  "transcript": {
    "full_text": "This is the transcribed meeting content...",
    "segments": [...],
    "word_count": 245,
    "confidence_average": 0.92
  }
}
```

### 5. `get_client_session_status`
Get the current status of a client recording session.

**Parameters:**
- `session_id` (required): ID of the session to check

**Example Response:**
```json
{
  "session_id": "meeting-2025-01-15-001",
  "status": "receiving_audio",
  "duration_seconds": 45.2,
  "chunks_received": 9,
  "total_audio_duration": 43.8,
  "config": {
    "sample_rate": 16000,
    "channels": 1,
    "chunk_duration": 5
  },
  "last_activity": 1705123456.789
}
```

## Client Implementation Examples

### Web Browser Implementation

```javascript
class MCPAudioRecorder {
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

            // Request microphone access
            this.stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 16000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true
                }
            });

            // Create MediaRecorder
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

            console.log('Recording started');
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

            // Send to MCP server
            const result = await this.mcpClient.callTool('send_audio_chunk', {
                session_id: this.sessionId,
                audio_data: base64,
                metadata: {
                    timestamp: Date.now(),
                    format: 'webm',
                    size: arrayBuffer.byteLength
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

            // Stop MCP recording session
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

    async getStatus() {
        return await this.mcpClient.callTool('get_client_session_status', {
            session_id: this.sessionId
        });
    }
}

// Usage example
async function startMeetingTranscription() {
    const sessionId = `meeting-${Date.now()}`;
    const recorder = new MCPAudioRecorder(mcpClient, sessionId);
    
    try {
        await recorder.startRecording();
        
        // Record for 30 seconds
        setTimeout(async () => {
            const result = await recorder.stopRecording();
            console.log('Final transcript:', result.transcript);
        }, 30000);
        
    } catch (error) {
        console.error('Recording failed:', error);
    }
}
```

### Python Desktop Implementation

```python
import asyncio
import base64
import pyaudio
import wave
import io
from mcp_client import MCPClient

class DesktopAudioRecorder:
    def __init__(self, mcp_client, session_id):
        self.mcp_client = mcp_client
        self.session_id = session_id
        self.audio = pyaudio.PyAudio()
        self.stream = None
        self.is_recording = False
        
        # Audio settings
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

            # Open audio stream
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
                    
                    # Send to MCP server
                    result = await self.mcp_client.call_tool('send_audio_chunk', {
                        'session_id': self.session_id,
                        'audio_data': base64_data,
                        'metadata': {
                            'timestamp': time.time(),
                            'format': 'wav',
                            'size': len(wav_data)
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
            
            # Stop MCP recording session
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
    
    recorder = DesktopAudioRecorder(mcp_client, session_id)
    
    try:
        await recorder.start_recording()
        
        # Record for 30 seconds
        await asyncio.sleep(30)
        
        result = await recorder.stop_recording()
        print(f"Final transcript: {result['transcript']}")
        
    except Exception as e:
        print(f"Recording failed: {e}")

if __name__ == "__main__":
    asyncio.run(main())
```

## Workflow

1. **Get Instructions**: Call `get_audio_instructions` to understand implementation requirements
2. **Start Session**: Call `start_client_recording` to initialize a recording session
3. **Capture & Send**: Implement client-side audio capture and use `send_audio_chunk` to forward audio data
4. **Monitor**: Use `get_client_session_status` to monitor session progress
5. **Complete**: Call `stop_client_recording` to finish and get the transcript

## Audio Format Requirements

- **Sample Rate**: 16000 Hz (recommended)
- **Channels**: 1 (mono)
- **Format**: WAV or raw PCM
- **Encoding**: Base64 for transmission
- **Chunk Size**: 5-second chunks (recommended)
- **Bit Depth**: 16-bit

## Error Handling

The client should handle these common scenarios:

- **Microphone Permission Denied**: Request user permission gracefully
- **Network Issues**: Implement retry logic for chunk transmission
- **Session Timeouts**: Monitor session status and restart if needed
- **Large Audio Files**: Break into manageable chunks to avoid memory issues

## Performance Considerations

- Use appropriate chunk sizes (5 seconds recommended)
- Implement client-side audio compression if needed
- Monitor bandwidth usage for real-time streaming
- Consider client-side buffering for unreliable connections

This client-side audio forwarding approach enables the Meeting Transcription Agent to work effectively in containerized environments while maintaining high-quality transcription capabilities.