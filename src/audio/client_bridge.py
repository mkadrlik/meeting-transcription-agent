"""
Client-side audio bridge for forwarding audio from client to server

This module handles audio data received from MCP clients and processes it
for transcription, since MCP servers don't have direct access to client hardware.
"""

import base64
import logging
import time
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)

class ClientAudioBridge:
    """Handles audio data forwarded from MCP clients"""
    
    def __init__(self):
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        self.audio_buffers: Dict[str, List[Dict[str, Any]]] = {}
    
    def start_client_recording(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a recording session that expects client-forwarded audio"""
        try:
            if session_id in self.active_sessions:
                raise ValueError(f"Session {session_id} is already active")
            
            # Initialize session for client audio
            self.active_sessions[session_id] = {
                'config': config,
                'status': 'waiting_for_audio',
                'start_time': time.time(),
                'chunk_count': 0,
                'total_audio_duration': 0
            }
            
            self.audio_buffers[session_id] = []
            
            logger.info(f"Started client recording session {session_id}")
            return {
                'session_id': session_id,
                'status': 'waiting_for_audio',
                'message': 'Session ready to receive audio from client',
                'instructions': {
                    'audio_format': 'WAV or raw PCM',
                    'encoding': 'base64',
                    'sample_rate': config.get('sample_rate', 16000),
                    'channels': config.get('channels', 1),
                    'chunk_size_ms': config.get('chunk_duration', 5) * 1000
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to start client recording session {session_id}: {str(e)}")
            raise
    
    def receive_audio_chunk(self, session_id: str, audio_data: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Receive and process audio chunk from client"""
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            # Decode base64 audio data
            try:
                audio_bytes = base64.b64decode(audio_data)
            except Exception as e:
                raise ValueError(f"Invalid base64 audio data: {str(e)}")
            
            # Store audio chunk
            chunk_info = {
                'data': audio_bytes,
                'timestamp': time.time(),
                'metadata': metadata or {},
                'size': len(audio_bytes)
            }
            
            self.audio_buffers[session_id].append(chunk_info)
            
            # Update session stats
            session['chunk_count'] += 1
            session['status'] = 'receiving_audio'
            session['last_chunk_time'] = time.time()
            
            # Calculate approximate audio duration (assuming 16-bit PCM)
            sample_rate = session['config'].get('sample_rate', 16000)
            channels = session['config'].get('channels', 1)
            bytes_per_sample = 2  # 16-bit
            duration_seconds = len(audio_bytes) / (sample_rate * channels * bytes_per_sample)
            session['total_audio_duration'] += duration_seconds
            
            logger.debug(f"Received audio chunk for session {session_id}: "
                        f"{len(audio_bytes)} bytes, ~{duration_seconds:.2f}s")
            
            return {
                'session_id': session_id,
                'status': 'chunk_received',
                'chunk_number': session['chunk_count'],
                'chunk_size_bytes': len(audio_bytes),
                'total_chunks': session['chunk_count'],
                'total_duration_seconds': session['total_audio_duration']
            }
            
        except Exception as e:
            logger.error(f"Failed to receive audio chunk for session {session_id}: {str(e)}")
            raise
    
    def stop_client_recording(self, session_id: str) -> Dict[str, Any]:
        """Stop client recording and return combined audio data"""
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            audio_chunks = self.audio_buffers.get(session_id, [])
            
            # Combine all audio chunks
            combined_audio = b''.join([chunk['data'] for chunk in audio_chunks])
            
            # Update session status
            session['status'] = 'completed'
            session['end_time'] = time.time()
            session['final_audio_size'] = len(combined_audio)
            
            # Clean up
            del self.audio_buffers[session_id]
            
            logger.info(f"Stopped client recording session {session_id}: "
                       f"{len(combined_audio)} bytes, {session['chunk_count']} chunks")
            
            return {
                'session_id': session_id,
                'status': 'completed',
                'total_chunks': session['chunk_count'],
                'total_duration_seconds': session['total_audio_duration'],
                'total_audio_bytes': len(combined_audio),
                'audio_data': combined_audio,  # Raw audio data for transcription
                'session_duration': session['end_time'] - session['start_time']
            }
            
        except Exception as e:
            logger.error(f"Failed to stop client recording session {session_id}: {str(e)}")
            raise
    
    def get_client_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of client recording session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        current_time = time.time()
        
        return {
            'session_id': session_id,
            'status': session['status'],
            'duration_seconds': current_time - session['start_time'],
            'chunks_received': session['chunk_count'],
            'total_audio_duration': session['total_audio_duration'],
            'config': session['config'],
            'last_activity': session.get('last_chunk_time', session['start_time'])
        }
    
    def get_audio_data(self, session_id: str) -> Optional[bytes]:
        """Get combined audio data for a session"""
        if session_id not in self.audio_buffers:
            return None
        
        chunks = self.audio_buffers[session_id]
        return b''.join([chunk['data'] for chunk in chunks])
    
    def cleanup_session(self, session_id: str) -> None:
        """Clean up session data"""
        if session_id in self.active_sessions:
            del self.active_sessions[session_id]
        if session_id in self.audio_buffers:
            del self.audio_buffers[session_id]
    
    def list_client_sessions(self) -> Dict[str, Dict[str, Any]]:
        """List all active client sessions"""
        return {
            session_id: {
                'status': session['status'],
                'chunk_count': session['chunk_count'],
                'duration': time.time() - session['start_time'],
                'total_audio_duration': session['total_audio_duration']
            }
            for session_id, session in self.active_sessions.items()
        }


class ClientAudioInstructions:
    """Provides instructions for client-side audio capture"""
    
    @staticmethod
    def get_web_audio_instructions() -> Dict[str, Any]:
        """Get instructions for web-based audio capture"""
        return {
            "type": "web_audio_api",
            "instructions": {
                "1_request_permission": "navigator.mediaDevices.getUserMedia({audio: true})",
                "2_create_recorder": "Use MediaRecorder API or AudioContext",
                "3_capture_chunks": "Record audio in 5-second chunks",
                "4_encode": "Convert to base64 before sending",
                "5_send_via_mcp": "Use send_audio_chunk tool"
            },
            "sample_code": {
                "javascript": """
// Example JavaScript for client-side audio capture
async function startMCPAudioRecording(sessionId) {
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const mediaRecorder = new MediaRecorder(stream);
    const chunks = [];
    
    mediaRecorder.ondataavailable = async (event) => {
        if (event.data.size > 0) {
            const audioBlob = event.data;
            const arrayBuffer = await audioBlob.arrayBuffer();
            const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
            
            // Send via MCP tool
            await mcpClient.callTool('send_audio_chunk', {
                session_id: sessionId,
                audio_data: base64,
                metadata: {
                    timestamp: Date.now(),
                    format: 'webm',
                    size: arrayBuffer.byteLength
                }
            });
        }
    };
    
    mediaRecorder.start(5000); // 5-second chunks
    return mediaRecorder;
}
                """
            },
            "recommended_settings": {
                "chunk_duration_ms": 5000,
                "sample_rate": 16000,
                "channels": 1,
                "bit_depth": 16,
                "format": "wav"
            }
        }
    
    @staticmethod
    def get_desktop_audio_instructions() -> Dict[str, Any]:
        """Get instructions for desktop application audio capture"""
        return {
            "type": "desktop_application",
            "instructions": {
                "1_select_device": "List available audio input devices",
                "2_configure_capture": "Set sample rate, channels, bit depth",
                "3_start_recording": "Begin audio capture in chunks",
                "4_encode_send": "Base64 encode and send via MCP tools"
            },
            "platforms": {
                "windows": "Use DirectSound, WASAPI, or similar",
                "macos": "Use Core Audio frameworks",
                "linux": "Use ALSA, PulseAudio, or JACK"
            },
            "mcp_integration": "Use MCP client libraries to call tools"
        }