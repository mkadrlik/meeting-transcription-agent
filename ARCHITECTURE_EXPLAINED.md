# Audio Bridge Architecture Explained

## 🔄 **Two-Part Solution for Docker Audio**

The audio system uses **TWO complementary components** to work around Docker's audio limitations:

### 1. **`src/audio/client_bridge.py`** (SERVER-SIDE) 
- ✅ **Runs INSIDE Docker container**
- ✅ **Part of the MCP server**
- ✅ **Receives audio data** from clients via MCP tools
- ✅ **Manages audio buffers** and session state
- ✅ **Processes incoming base64-encoded audio**

### 2. **`src/audio/host_bridge.py`** (CLIENT-SIDE)
- ✅ **Runs ON HOST machine** (outside Docker)
- ✅ **Captures real microphone audio** using PyAudio
- ✅ **Converts audio to base64 WAV format**
- ✅ **Sends audio TO the Docker container** via HTTP

## 🏗️ **Complete Architecture:**

```
┌─────────────────────┐    HTTP/MCP     ┌──────────────────────────┐
│   HOST MACHINE      │    Request      │    DOCKER CONTAINER      │
│                     │ ──────────────> │                          │
│ src/audio/host_bridge.py│             │ client_bridge.py         │
│   ↑                 │                 │   ↓                      │
│ PyAudio (mic)       │                 │ MCP Server Tools         │
│                     │                 │   ↓                      │
│                     │                 │ Transcription Service    │
│                     │                 │   ↓                      │
│                     │ <────────────── │ Whisper AI Processing    │
│                     │    Transcript   │                          │
└─────────────────────┘                 └──────────────────────────┘
```

## 🎯 **Why Both Are Needed:**

### **Without `client_bridge.py`:**
- ❌ Docker container has no way to receive audio data
- ❌ No MCP tools for audio forwarding
- ❌ No session management for incoming audio

### **Without `src/audio/host_bridge.py`:**
- ❌ Docker can't access host microphone directly
- ❌ ALSA errors (as you experienced)
- ❌ No way to capture real audio

### **With BOTH Together:**
- ✅ Host captures real microphone audio
- ✅ Docker processes audio with Whisper AI
- ✅ Complete client-server audio solution
- ✅ Bypasses Docker audio limitations

## 📋 **Data Flow:**

1. **Host microphone** → `src/audio/host_bridge.py` (PyAudio capture)
2. **Raw audio** → Base64 WAV encoding
3. **HTTP POST** → Docker container MCP gateway
4. **MCP tools** → `client_bridge.py` (receives/stores audio)
5. **Audio buffer** → Transcription service
6. **Whisper AI** → Text transcript
7. **HTTP response** → Back to host with results

## 🚀 **Usage:**

Both components work together automatically when you run:
```bash
./start_recording.sh
```

This starts:
1. **Docker MCP server** (includes `client_bridge.py`)
2. **Host audio bridge** (runs `src/audio/host_bridge.py`)
3. **Complete recording workflow**

## ✅ **Summary:**

- **`client_bridge.py`** = Server-side audio receiver (in Docker)
- **`src/audio/host_bridge.py`** = Client-side audio capturer (on host)
- **Both required** for complete Docker audio solution
- **They communicate** via HTTP/MCP protocol
- **Result:** Working audio transcription despite Docker limitations