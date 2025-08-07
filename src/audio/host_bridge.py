#!/usr/bin/env python3
"""
Host Audio Bridge for Dockerized MCP Server
Captures audio on host and forwards to MCP server running in Docker
"""

import asyncio
import base64
import json
import logging
import time
import sys
import tempfile
import wave
from pathlib import Path
from typing import cast

import numpy as np
import pyaudio
import requests

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class HostAudioBridge:
    def __init__(self, mcp_gateway_url="http://192.168.50.20:9000"):
        self.mcp_gateway_url = mcp_gateway_url.rstrip('/')
        self.session_id = f"host-bridge-{int(time.time())}"
        self.is_recording = False
        self.chunk_count = 0
        
    def check_mcp_server(self):
        """Check if MCP server is accessible"""
        try:
            # Try to list available tools
            response = requests.post(
                f"{self.mcp_gateway_url}/tools/list",
                timeout=5
            )
            if response.status_code == 200:
                tools = response.json()
                logger.info(f"✅ MCP Server accessible. Available tools: {len(tools)}")
                return True
            else:
                logger.error(f"❌ MCP Server returned status: {response.status_code}")
                return False
        except Exception as e:
            logger.error(f"❌ Cannot connect to MCP Server at {self.mcp_gateway_url}: {e}")
            return False
    
    def call_mcp_tool(self, tool_name, arguments):
        """Call an MCP tool via the gateway"""
        try:
            payload = {
                "name": tool_name,
                "arguments": arguments
            }
            
            response = requests.post(
                f"{self.mcp_gateway_url}/tools/call",
                json=payload,
                timeout=30
            )
            
            if response.status_code == 200:
                return response.json()
            else:
                logger.error(f"MCP tool call failed: {response.status_code} - {response.text}")
                return None
                
        except Exception as e:
            logger.error(f"Error calling MCP tool {tool_name}: {e}")
            return None
    
    def audio_to_base64_wav(self, audio_data, sample_rate=16000):
        """Convert raw audio data to base64-encoded WAV"""
        try:
            # Create temporary WAV file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_path = temp_file.name
                
            # Write WAV file - use explicit variable assignment to avoid Pylint confusion
            wav_writer = wave.open(temp_path, 'wb')
            wav_writer.setnchannels(1)  # Mono
            wav_writer.setsampwidth(2)  # 16-bit
            wav_writer.setframerate(sample_rate)
            wav_writer.writeframes(audio_data)
            wav_writer.close()
            
            # Read and encode to base64
            with open(temp_path, 'rb') as f:
                wav_data = f.read()
            
            # Clean up
            Path(temp_path).unlink()
            
            return base64.b64encode(wav_data).decode('utf-8')
            
        except Exception as e:
            logger.error(f"Error converting audio to base64: {e}")
            return None
    
    def find_speaker_monitor_device(self, audio):
        """Find speaker monitor/loopback device for capturing output audio"""
        try:
            print("\n🔍 Looking for speaker monitor devices...")
            for i in range(audio.get_device_count()):
                info = audio.get_device_info_by_index(i)
                name = info.get('name', '').lower()
                
                # Look for monitor, loopback, or stereo mix devices
                if any(keyword in name for keyword in ['monitor', 'loopback', 'stereo mix', 'what u hear']):
                    if int(info.get('maxInputChannels', 0)) > 0:
                        print(f"  📻 Found monitor device {i}: {info['name']}")
                        return i
            
            print("  ⚠️ No monitor device found - will capture microphone only")
            return None
        except Exception as e:
            logger.error(f"Error finding monitor device: {e}")
            return None

    def start_recording(self):
        """Start host-side dual audio capture (mic + speaker) and forward to MCP server"""
        print("🎤🔊 DUAL Audio Bridge for Dockerized MCP Server")
        print("📱 Captures: Microphone + Bluetooth Headphone Output")
        print(f"🔗 MCP Gateway: {self.mcp_gateway_url}")
        print(f"📝 Session ID: {self.session_id}")
        print("=" * 60)
        
        # Check MCP server connection
        if not self.check_mcp_server():
            print("❌ Cannot connect to MCP Server. Make sure Docker container is running:")
            print("   ./scripts/run.sh start")
            return
        
        # Start MCP client recording session
        print("🚀 Starting MCP client recording session...")
        result = self.call_mcp_tool('start_client_recording', {
            'session_id': self.session_id,
            'sample_rate': 16000,
            'channels': 1,
            'chunk_duration': 5
        })
        
        if not result:
            print("❌ Failed to start MCP recording session")
            return
            
        print(f"✅ MCP session started: {result}")
        
        # Audio settings
        CHUNK = 1024
        FORMAT = pyaudio.paInt16
        CHANNELS = 1
        RATE = 16000
        RECORD_SECONDS_PER_CHUNK = 5  # Send every 5 seconds
        
        # Initialize PyAudio
        audio = pyaudio.PyAudio()
        
        print("\n🔍 Available audio devices:")
        input_devices = []
        output_devices = []
        
        for i in range(audio.get_device_count()):
            info = audio.get_device_info_by_index(i)
            if int(info['maxInputChannels']) > 0:
                input_devices.append((i, info['name']))
                print(f"  🎤 Input {i}: {info['name']}")
            if int(info['maxOutputChannels']) > 0:
                output_devices.append((i, info['name']))
                print(f"  🔊 Output {i}: {info['name']}")
        
        # Find speaker monitor device for capturing output
        speaker_monitor_device = self.find_speaker_monitor_device(audio)
        
        # Open dual audio streams
        try:
            # Microphone stream
            mic_stream = audio.open(
                format=FORMAT,
                channels=CHANNELS,
                rate=RATE,
                input=True,
                frames_per_buffer=CHUNK
            )
            
            # Speaker monitor stream (if available)
            speaker_stream = None
            if speaker_monitor_device is not None:
                try:
                    speaker_stream = audio.open(
                        format=FORMAT,
                        channels=CHANNELS,
                        rate=RATE,
                        input=True,
                        input_device_index=speaker_monitor_device,
                        frames_per_buffer=CHUNK
                    )
                    print(f"✅ Speaker monitor enabled on device {speaker_monitor_device}")
                except Exception as e:
                    print(f"⚠️ Could not open speaker monitor: {e}")
                    speaker_stream = None
            
            print("\n🔴 DUAL RECORDING TO DOCKERIZED MCP SERVER")
            print("🎤 Microphone: Capturing your voice")
            if speaker_stream:
                print("🔊 Speaker Monitor: Capturing other participants")
            else:
                print("⚠️ Speaker Monitor: Not available (microphone only)")
            print("� Audio captured on host, processed in container!")
            print("📋 Press Ctrl+C to stop and get complete transcript")
            print("-" * 60)
            
            self.is_recording = True
            mic_frames = []
            speaker_frames = []
            last_send_time = time.time()
            
            while self.is_recording:
                try:
                    # Read microphone audio
                    mic_data = mic_stream.read(CHUNK, exception_on_overflow=False)
                    mic_frames.append(mic_data)
                    
                    # Read speaker audio (if available)
                    if speaker_stream:
                        try:
                            speaker_data = speaker_stream.read(CHUNK, exception_on_overflow=False)
                            speaker_frames.append(speaker_data)
                        except:
                            # If speaker stream fails, continue with microphone only
                            pass
                    
                    # Send every 5 seconds
                    current_time = time.time()
                    if current_time - last_send_time >= RECORD_SECONDS_PER_CHUNK:
                        self.chunk_count += 1
                        print(f"\n📤 Sending dual audio chunk #{self.chunk_count} to MCP server...")
                        
                        # Combine microphone and speaker audio
                        mic_audio = b''.join(mic_frames)
                        
                        if speaker_frames:
                            speaker_audio = b''.join(speaker_frames)
                            # Mix both audio sources (simple addition)
                            combined_audio = self.mix_audio_sources(mic_audio, speaker_audio)
                            print("🎵 Mixed: Microphone + Speaker audio")
                        else:
                            combined_audio = mic_audio
                            print("🎤 Microphone audio only")
                        
                        # Convert to base64 WAV
                        base64_audio = self.audio_to_base64_wav(combined_audio, RATE)
                        
                        if base64_audio:
                            # Send to MCP server
                            result = self.call_mcp_tool('send_audio_chunk', {
                                'session_id': self.session_id,
                                'audio_data': base64_audio,
                                'metadata': {
                                    'timestamp': current_time,
                                    'format': 'wav',
                                    'chunk_number': self.chunk_count,
                                    'sources': 'microphone+speaker' if speaker_frames else 'microphone'
                                }
                            })
                            
                            if result:
                                print(f"✅ Chunk #{self.chunk_count} sent successfully")
                                print(f"📊 Status: {result.get('status', 'unknown')}")
                            else:
                                print(f"❌ Failed to send chunk #{self.chunk_count}")
                        
                        # Reset for next chunk
                        mic_frames = []
                        speaker_frames = []
                        last_send_time = current_time
                        
                except KeyboardInterrupt:
                    print("\n⏹️ Stopping recording...")
                    self.is_recording = False
                    break
                except Exception as e:
                    print(f"⚠️ Recording error: {e}")
                    continue
            
            # Stop audio streams
            mic_stream.stop_stream()
            mic_stream.close()
            if speaker_stream:
                speaker_stream.stop_stream()
                speaker_stream.close()
            audio.terminate()
            
            # Stop MCP client recording and get transcript
            self.get_final_transcript()
            
        except Exception as e:
            print(f"❌ Failed to start audio recording: {e}")
            audio.terminate()

    def mix_audio_sources(self, mic_audio, speaker_audio):
        """Mix microphone and speaker audio streams"""
        try:
            # Convert bytes to numpy arrays (16-bit signed integers)
            mic_array = np.frombuffer(mic_audio, dtype=np.int16)
            speaker_array = np.frombuffer(speaker_audio, dtype=np.int16)
            
            # Make arrays same length
            min_length = min(len(mic_array), len(speaker_array))
            mic_array = mic_array[:min_length]
            speaker_array = speaker_array[:min_length]
            
            # Mix audio (reduce volume to prevent clipping)
            mixed = (mic_array * 0.6 + speaker_array * 0.4).astype(np.int16)
            
            return mixed.tobytes()
            
        except ImportError:
            # Fallback: just use microphone if numpy not available
            logger.warning("NumPy not available for audio mixing, using microphone only")
            return mic_audio
        except Exception as e:
            logger.error(f"Error mixing audio: {e}")
            return mic_audio
    
    def get_final_transcript(self):
        """Get final transcript from MCP server"""
        print("\n📄 Getting final transcript from MCP server...")
        
        result = self.call_mcp_tool('stop_client_recording', {
            'session_id': self.session_id
        })
        
        if result:
            print("\n" + "=" * 60)
            print("📋 FINAL MEETING TRANSCRIPT (from MCP Server)")
            print("=" * 60)
            
            transcript = result.get('transcript', {})
            full_text = transcript.get('full_text', 'No transcript available')
            
            print(full_text)
            
            # Show statistics
            word_count = transcript.get('word_count', 0)
            duration = result.get('session_duration', 0)
            confidence = transcript.get('confidence_average', 0)
            
            print(f"\n📊 STATISTICS:")
            print(f"   📝 Total Words: {word_count}")
            print(f"   ⏱️ Duration: {duration:.1f} seconds")
            print(f"   🎯 Confidence: {confidence:.2f}")
            print(f"   📤 Chunks Sent: {self.chunk_count}")
            print(f"   🐳 Processed by: Docker MCP Server")
            
            # Save transcript
            timestamp = int(time.time())
            filename = f"mcp_transcript_{timestamp}.txt"
            
            with open(filename, 'w', encoding='utf-8') as f:
                f.write(f"Meeting Transcript - {time.ctime()}\n")
                f.write("Generated by Host Audio Bridge -> Docker MCP Server\n")
                f.write("=" * 60 + "\n\n")
                f.write(full_text)
                f.write(f"\n\nSTATISTICS:\n")
                f.write(f"Total Words: {word_count}\n")
                f.write(f"Duration: {duration:.1f} seconds\n")
                f.write(f"Confidence: {confidence:.2f}\n")
                f.write(f"Chunks Sent: {self.chunk_count}\n")
            
            print(f"\n💾 Transcript saved to: {filename}")
            print("✅ Host Audio Bridge session completed!")
            
        else:
            print("❌ Failed to get final transcript from MCP server")

def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Host Audio Bridge for Dockerized MCP Server")
    parser.add_argument('--gateway-url', default='http://192.168.50.20:9000',
                       help='MCP Gateway URL (default: http://192.168.50.20:9000)')
    
    args = parser.parse_args()
    
    bridge = HostAudioBridge(args.gateway_url)
    bridge.start_recording()

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Audio bridge stopped by user")
    except Exception as e:
        print(f"❌ Fatal error: {e}")