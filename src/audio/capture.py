"""
Audio capture module for meeting transcription

Handles microphone and speaker audio capture using PyAudio and system audio routing.
"""

import asyncio
import logging
import threading
import time
import wave
from typing import Dict, List, Any, Optional, AsyncGenerator
import io

try:
    import pyaudio
    import numpy as np
    PYAUDIO_AVAILABLE = True
except ImportError:
    PYAUDIO_AVAILABLE = False
    pyaudio = None
    np = None

logger = logging.getLogger(__name__)

class AudioStream:
    """Represents an active audio stream"""
    
    def __init__(self, session_id: str, config: Dict[str, Any]):
        self.session_id = session_id
        self.config = config
        self.is_recording = False
        self.audio_buffer = []
        self.stream = None
        self.thread = None
        self.stop_event = threading.Event()
    
    def start(self):
        """Start the audio stream"""
        self.is_recording = True
        self.stop_event.clear()
    
    def stop(self):
        """Stop the audio stream"""
        self.is_recording = False
        self.stop_event.set()
        if self.thread and self.thread.is_alive():
            self.thread.join(timeout=5.0)
    
    def get_audio_data(self) -> bytes:
        """Get accumulated audio data"""
        if not self.audio_buffer:
            return b''
        
        # Combine all audio chunks
        audio_data = b''.join(self.audio_buffer)
        self.audio_buffer.clear()
        return audio_data


class AudioCapture:
    """Handles audio capture from microphones and speakers"""
    
    def __init__(self, settings):
        self.settings = settings
        self.pa = None
        self.active_streams: Dict[str, AudioStream] = {}
        
        if not PYAUDIO_AVAILABLE:
            logger.warning("PyAudio not available. Audio capture will be limited.")
        else:
            self._initialize_pyaudio()
    
    def _initialize_pyaudio(self):
        """Initialize PyAudio"""
        try:
            self.pa = pyaudio.PyAudio()
            logger.info("PyAudio initialized successfully")
        except Exception as e:
            logger.error(f"Failed to initialize PyAudio: {str(e)}")
            self.pa = None
    
    async def list_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """List available audio input and output devices"""
        if not self.pa:
            return {
                "input_devices": [{"id": "default", "name": "Default Microphone", "channels": 1}],
                "output_devices": [{"id": "default", "name": "Default Speaker", "channels": 2}],
                "error": "PyAudio not available - showing default devices only"
            }
        
        try:
            input_devices = []
            output_devices = []
            
            device_count = self.pa.get_device_count()
            
            for i in range(device_count):
                try:
                    device_info = self.pa.get_device_info_by_index(i)
                    
                    device_data = {
                        "id": i,
                        "name": device_info.get('name', f'Device {i}'),
                        "channels": device_info.get('maxInputChannels', 0),
                        "sample_rate": device_info.get('defaultSampleRate', 44100),
                        "host_api": device_info.get('hostApi', 0)
                    }
                    
                    # Input devices (microphones)
                    if device_info.get('maxInputChannels', 0) > 0:
                        input_devices.append(device_data.copy())
                    
                    # Output devices (speakers)
                    if device_info.get('maxOutputChannels', 0) > 0:
                        output_device_data = device_data.copy()
                        output_device_data['channels'] = device_info.get('maxOutputChannels', 0)
                        output_devices.append(output_device_data)
                        
                except Exception as e:
                    logger.warning(f"Error getting info for device {i}: {str(e)}")
                    continue
            
            return {
                "input_devices": input_devices,
                "output_devices": output_devices
            }
            
        except Exception as e:
            logger.error(f"Error listing audio devices: {str(e)}")
            return {
                "input_devices": [],
                "output_devices": [],
                "error": str(e)
            }
    
    def _audio_callback(self, in_data, frame_count, time_info, status, stream: AudioStream):
        """Callback function for audio stream"""
        if stream.is_recording and in_data:
            stream.audio_buffer.append(in_data)
        
        return (None, pyaudio.paContinue)
    
    def _record_thread(self, stream: AudioStream):
        """Thread function for recording audio"""
        if not self.pa:
            logger.error("PyAudio not available for recording")
            return
        
        try:
            config = stream.config
            device_id = None
            
            # Try to find device by name or use as ID
            microphone_device = config['microphone_device']
            if isinstance(microphone_device, str) and microphone_device != 'default':
                # Try to find device by name
                devices = asyncio.run(self.list_devices())
                for device in devices.get('input_devices', []):
                    if device['name'] == microphone_device:
                        device_id = device['id']
                        break
                
                # If not found by name, try to parse as integer ID
                if device_id is None:
                    try:
                        device_id = int(microphone_device)
                    except ValueError:
                        logger.warning(f"Could not find microphone device: {microphone_device}")
                        device_id = None
            
            # Open audio stream
            audio_stream = self.pa.open(
                format=pyaudio.paInt16,
                channels=config.get('channels', 1),
                rate=config.get('sample_rate', 16000),
                input=True,
                input_device_index=device_id,
                frames_per_buffer=1024,
                stream_callback=lambda in_data, frame_count, time_info, status: 
                    self._audio_callback(in_data, frame_count, time_info, status, stream)
            )
            
            stream.stream = audio_stream
            audio_stream.start_stream()
            
            logger.info(f"Started recording for session {stream.session_id}")
            
            # Keep recording until stop event is set
            while not stream.stop_event.wait(0.1):
                if not audio_stream.is_active():
                    break
            
            # Clean up
            audio_stream.stop_stream()
            audio_stream.close()
            logger.info(f"Stopped recording for session {stream.session_id}")
            
        except Exception as e:
            logger.error(f"Error in recording thread for session {stream.session_id}: {str(e)}")
            stream.is_recording = False
    
    async def start_capture(self, session_config: Dict[str, Any]) -> AudioStream:
        """Start audio capture for a session"""
        session_id = session_config['session_id']
        
        if session_id in self.active_streams:
            raise ValueError(f"Session {session_id} is already active")
        
        # Create audio stream
        stream = AudioStream(session_id, session_config)
        self.active_streams[session_id] = stream
        
        # Start recording
        stream.start()
        
        if PYAUDIO_AVAILABLE and self.pa:
            # Start recording thread
            stream.thread = threading.Thread(
                target=self._record_thread,
                args=(stream,),
                daemon=True
            )
            stream.thread.start()
        else:
            logger.warning(f"Audio capture not available for session {session_id} - PyAudio not installed")
        
        return stream
    
    async def stop_capture(self, stream: AudioStream):
        """Stop audio capture for a stream"""
        stream.stop()
        
        # Remove from active streams
        if stream.session_id in self.active_streams:
            del self.active_streams[stream.session_id]
    
    async def get_audio_chunk(self, session_id: str) -> Optional[bytes]:
        """Get the next audio chunk for a session"""
        if session_id not in self.active_streams:
            return None
        
        stream = self.active_streams[session_id]
        return stream.get_audio_data()
    
    def __del__(self):
        """Cleanup resources"""
        # Stop all active streams
        for stream in list(self.active_streams.values()):
            stream.stop()
        
        # Terminate PyAudio
        if self.pa:
            try:
                self.pa.terminate()
            except Exception as e:
                logger.error(f"Error terminating PyAudio: {str(e)}")


class MockAudioCapture(AudioCapture):
    """Mock audio capture for testing when PyAudio is not available"""
    
    def __init__(self, settings):
        self.settings = settings
        self.active_streams: Dict[str, AudioStream] = {}
        logger.info("Using mock audio capture (PyAudio not available)")
    
    async def list_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """Return mock device list"""
        return {
            "input_devices": [
                {"id": "mock_mic_1", "name": "Mock Microphone 1", "channels": 1},
                {"id": "mock_mic_2", "name": "Mock Microphone 2", "channels": 2}
            ],
            "output_devices": [
                {"id": "mock_speaker_1", "name": "Mock Speaker 1", "channels": 2},
                {"id": "mock_speaker_2", "name": "Mock Speaker 2", "channels": 2}
            ],
            "note": "Mock devices - PyAudio not available"
        }
    
    async def start_capture(self, session_config: Dict[str, Any]) -> AudioStream:
        """Start mock audio capture"""
        session_id = session_config['session_id']
        
        if session_id in self.active_streams:
            raise ValueError(f"Session {session_id} is already active")
        
        stream = AudioStream(session_id, session_config)
        stream.start()
        self.active_streams[session_id] = stream
        
        logger.info(f"Started mock audio capture for session {session_id}")
        return stream
    
    async def get_audio_chunk(self, session_id: str) -> Optional[bytes]:
        """Return mock audio data"""
        if session_id not in self.active_streams:
            return None
        
        # Generate some mock audio data (silence)
        mock_data = b'\x00' * 1024  # 1KB of silence
        return mock_data