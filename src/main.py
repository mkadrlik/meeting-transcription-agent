#!/usr/bin/env python3
"""
Meeting Transcription Agent MCP Server

This MCP server provides tools for capturing and transcribing meeting audio
from user-selected microphones and speakers.
"""

import asyncio
import json
import logging
import os
import time
from pathlib import Path
from typing import Optional, Dict, Any, List, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent
import mcp.types as types

from .audio.capture import AudioCapture
from .audio.client_bridge import ClientAudioBridge, ClientAudioInstructions
from .transcription.service import TranscriptionService
from .config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeetingTranscriptionServer:
    def __init__(self):
        self.settings = Settings()
        self.audio_capture = AudioCapture(self.settings)
        self.client_bridge = ClientAudioBridge()
        self.transcription_service = TranscriptionService(self.settings)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def start_recording_session(self, session_id: str, audio_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new recording session"""
        try:
            # Validate audio configuration
            microphone_device = audio_config.get('microphone_device')
            speaker_device = audio_config.get('speaker_device')
            
            if not microphone_device:
                raise ValueError("Microphone device must be specified")
            if not speaker_device:
                raise ValueError("Speaker device must be specified")
            
            # Get audio parameters from environment/settings with defaults
            sample_rate = self.settings.get('DEFAULT_SAMPLE_RATE', 16000)
            channels = self.settings.get('DEFAULT_CHANNELS', 1)
            chunk_duration = self.settings.get('DEFAULT_CHUNK_DURATION', 30)
            
            # Initialize audio capture for this session
            session_config = {
                'session_id': session_id,
                'microphone_device': microphone_device,
                'speaker_device': speaker_device,
                'sample_rate': int(sample_rate),
                'channels': int(channels),
                'chunk_duration': int(chunk_duration)
            }
            
            # Start audio capture
            audio_stream = await self.audio_capture.start_capture(session_config)
            
            # Store session information
            self.active_sessions[session_id] = {
                'config': session_config,
                'audio_stream': audio_stream,
                'transcripts': [],
                'status': 'recording',
                'start_time': asyncio.get_event_loop().time()
            }
            
            logger.info(f"Started recording session {session_id}")
            return {
                'session_id': session_id,
                'status': 'recording',
                'message': 'Recording session started successfully'
            }
            
        except Exception as e:
            logger.error(f"Failed to start recording session {session_id}: {str(e)}")
            raise
    
    async def stop_recording_session(self, session_id: str) -> Dict[str, Any]:
        """Stop a recording session and return final transcript"""
        try:
            if session_id not in self.active_sessions:
                raise ValueError(f"Session {session_id} not found")
            
            session = self.active_sessions[session_id]
            
            # Stop audio capture
            await self.audio_capture.stop_capture(session['audio_stream'])
            
            # Get final transcript
            final_transcript = await self.transcription_service.get_final_transcript(session_id)
            
            # Update session status
            session['status'] = 'completed'
            session['final_transcript'] = final_transcript
            session['end_time'] = asyncio.get_event_loop().time()
            
            logger.info(f"Stopped recording session {session_id}")
            return {
                'session_id': session_id,
                'status': 'completed',
                'transcript': final_transcript,
                'duration': session['end_time'] - session['start_time']
            }
            
        except Exception as e:
            logger.error(f"Failed to stop recording session {session_id}: {str(e)}")
            raise
    
    async def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get the current status of a recording session"""
        if session_id not in self.active_sessions:
            raise ValueError(f"Session {session_id} not found")
        
        session = self.active_sessions[session_id]
        current_time = asyncio.get_event_loop().time()
        
        return {
            'session_id': session_id,
            'status': session['status'],
            'duration': current_time - session['start_time'],
            'transcript_count': len(session['transcripts']),
            'config': session['config']
        }
    
    async def list_audio_devices(self) -> Dict[str, Union[List[Dict[str, Any]], str]]:
        """List available audio input and output devices"""
        return self.audio_capture.list_devices()
    
    def start_client_recording(self, session_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a client-side recording session that receives audio from the client"""
        return self.client_bridge.start_client_recording(session_id, config)
    
    def receive_audio_chunk(self, session_id: str, audio_data: str,
                           metadata: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Receive an audio chunk from the client"""
        return self.client_bridge.receive_audio_chunk(session_id, audio_data, metadata)
    
    async def stop_client_recording(self, session_id: str) -> Dict[str, Any]:
        """Stop client recording and process the complete audio"""
        try:
            # Get the complete audio data from the client bridge (synchronous call)
            result = self.client_bridge.stop_client_recording(session_id)
            audio_data = result.get('audio_data')
            
            if audio_data and len(audio_data) > 0:
                # Process the audio through transcription service (async calls)
                session_config = {'sample_rate': 16000, 'channels': 1}
                transcript_result = await self.transcription_service.transcribe_audio_chunk(
                    session_id, audio_data, session_config
                )
                
                # Get the final formatted transcript (async call)
                final_transcript = await self.transcription_service.get_final_transcript(session_id)
                result['transcript'] = final_transcript
                
                logger.info(f"Completed client recording session {session_id} with transcript")
            else:
                logger.warning(f"No audio data received for session {session_id}")
                result['transcript'] = {'full_text': '', 'segments': [], 'word_count': 0}
            
            return result
            
        except Exception as e:
            logger.error(f"Failed to stop client recording session {session_id}: {str(e)}")
            raise
    
    def get_client_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of client recording session"""
        return self.client_bridge.get_client_session_status(session_id)
    
    def get_audio_instructions(self, instruction_type: str = "web_audio") -> Dict[str, Any]:
        """Get instructions for client-side audio capture"""
        if instruction_type == "web_audio":
            return ClientAudioInstructions.get_web_audio_instructions()
        elif instruction_type == "desktop":
            return ClientAudioInstructions.get_desktop_audio_instructions()
        else:
            raise ValueError(f"Unknown instruction type: {instruction_type}")
    
    async def export_transcript_to_file(self, session_id: str, format: str = "json",
                                      file_path: Optional[str] = None) -> Dict[str, Any]:
        """Export transcript to a file on disk"""
        try:
            # Get the formatted transcript content
            transcript_content = await self.transcription_service.export_transcript(session_id, format)
            
            # Determine file path if not provided
            if not file_path:
                # Create exports directory if it doesn't exist
                exports_dir = Path("/tmp/transcripts")
                exports_dir.mkdir(parents=True, exist_ok=True)
                
                # Generate filename with timestamp
                timestamp = int(time.time())
                file_extension = format.lower()
                file_path = str(exports_dir / f"{session_id}_{timestamp}.{file_extension}")
            else:
                # Ensure directory exists for provided path
                file_path_obj = Path(file_path)
                file_path_obj.parent.mkdir(parents=True, exist_ok=True)
            
            # Write content to file
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(transcript_content)
            
            # Get file stats
            file_stats = os.stat(file_path)
            file_size = file_stats.st_size
            
            logger.info(f"Exported transcript for session {session_id} to {file_path}")
            
            return {
                'session_id': session_id,
                'format': format,
                'file_path': file_path,
                'file_size_bytes': file_size,
                'export_timestamp': time.time(),
                'content_preview': transcript_content[:200] + ('...' if len(transcript_content) > 200 else ''),
                'success': True
            }
            
        except Exception as e:
            logger.error(f"Failed to export transcript for session {session_id}: {str(e)}")
            return {
                'session_id': session_id,
                'format': format,
                'file_path': file_path,
                'error': str(e),
                'success': False
            }
    
    async def list_exported_transcripts(self, exports_dir: str = "/tmp/transcripts") -> Dict[str, Any]:
        """List all exported transcript files"""
        try:
            exports_path = Path(exports_dir)
            
            if not exports_path.exists():
                return {
                    'exports_directory': str(exports_path),
                    'files': [],
                    'total_files': 0,
                    'total_size_bytes': 0
                }
            
            files = []
            total_size = 0
            
            for file_path in exports_path.iterdir():
                if file_path.is_file():
                    stats = file_path.stat()
                    file_info = {
                        'filename': file_path.name,
                        'full_path': str(file_path),
                        'size_bytes': stats.st_size,
                        'modified_timestamp': stats.st_mtime,
                        'format': file_path.suffix.lstrip('.').lower()
                    }
                    
                    # Try to extract session_id from filename
                    if '_' in file_path.stem:
                        session_id = file_path.stem.split('_')[0]
                        file_info['session_id'] = session_id
                    
                    files.append(file_info)
                    total_size += stats.st_size
            
            # Sort by modification time (newest first)
            files.sort(key=lambda x: x['modified_timestamp'], reverse=True)  # type: ignore
            
            return {
                'exports_directory': str(exports_path),
                'files': files,
                'total_files': len(files),
                'total_size_bytes': total_size
            }
            
        except Exception as e:
            logger.error(f"Failed to list exported transcripts: {str(e)}")
            return {
                'exports_directory': exports_dir,
                'error': str(e),
                'files': [],
                'total_files': 0,
                'total_size_bytes': 0
            }
    
    async def get_device_selection_options(self, session_id: str) -> Dict[str, Any]:
        """Get available audio devices formatted for easy selection"""
        try:
            devices = self.audio_capture.list_devices()
            
            input_devices = devices.get('input_devices', [])
            output_devices = devices.get('output_devices', [])
            
            # Format for easy selection
            microphone_options = []
            for i, device in enumerate(input_devices):
                if isinstance(device, dict):
                    device_name = device.get('name', f'Unknown Input Device {i}')
                    device_id = device.get('id', device_name)
                    microphone_options.append({
                        'id': device_id,
                        'name': device_name,
                        'description': device.get('description', ''),
                        'selection_example': f'start_recording {{"session_id": "{session_id}", "microphone_device": "{device_id}", "speaker_device": "<speaker_id>"}}'
                    })
            
            speaker_options = []
            for i, device in enumerate(output_devices):
                if isinstance(device, dict):
                    device_name = device.get('name', f'Unknown Output Device {i}')
                    device_id = device.get('id', device_name)
                    speaker_options.append({
                        'id': device_id,
                        'name': device_name,
                        'description': device.get('description', ''),
                        'selection_example': f'start_recording {{"session_id": "{session_id}", "microphone_device": "<microphone_id>", "speaker_device": "{device_id}"}}'
                    })
            
            return {
                'session_id': session_id,
                'available_microphones': microphone_options,
                'available_speakers': speaker_options,
                'workflow_instructions': {
                    'step1': 'Choose a microphone from available_microphones list',
                    'step2': 'Choose a speaker from available_speakers list',
                    'step3': 'Call start_recording again with both device IDs specified'
                },
                'usage_note': 'Copy the device "id" field from your selected devices and use them in the start_recording call'
            }
            
        except Exception as e:
            logger.error(f"Failed to get device selection options: {str(e)}")
            return {
                'session_id': session_id,
                'error': str(e),
                'available_microphones': [],
                'available_speakers': []
            }
    
    async def get_transcript_content_for_editor(self, session_id: str, format: str = "txt",
                                              include_metadata: bool = False) -> str:
        """Get transcript content formatted for VS Code editor"""
        try:
            # Get the final transcript
            final_transcript = await self.transcription_service.get_final_transcript(session_id)
            
            if format.lower() == "txt":
                # Return plain text - clean and ready for editor
                content = final_transcript.get('full_text', '')
                if include_metadata:
                    metadata_info = f"""# Meeting Transcript - Session: {session_id}
# Duration: {final_transcript.get('duration', 0):.1f} seconds
# Word Count: {final_transcript.get('word_count', 0)}
# Confidence: {final_transcript.get('confidence_average', 0):.2f}
# Post-processed: {final_transcript.get('post_processed', False)}

{content}"""
                    return metadata_info
                return content
            
            elif format.lower() == "json":
                # Return formatted JSON
                return json.dumps(final_transcript, indent=2)
            
            elif format.lower() == "srt":
                # Return SRT subtitle format
                return await self.transcription_service.export_transcript(session_id, "srt")
            
            elif format.lower() == "markdown":
                # Return markdown format
                content = final_transcript.get('full_text', '')
                markdown_content = f"""# Meeting Transcript

**Session ID:** {session_id}
**Duration:** {final_transcript.get('duration', 0):.1f} seconds
**Word Count:** {final_transcript.get('word_count', 0)}
**Average Confidence:** {final_transcript.get('confidence_average', 0):.2f}
**Post-processed:** {final_transcript.get('post_processed', False)}

## Transcript

{content}
"""
                if include_metadata and final_transcript.get('segments'):
                    markdown_content += "\n\n## Segments\n\n"
                    for i, segment in enumerate(final_transcript['segments'], 1):
                        timestamp = segment.get('timestamp', 0)
                        confidence = segment.get('confidence', 0)
                        text = segment.get('text', '')
                        markdown_content += f"**{i}.** `{timestamp:.1f}s` (confidence: {confidence:.2f}) {text}\n\n"
                
                return markdown_content
            
            else:
                raise ValueError(f"Unsupported format: {format}")
                
        except Exception as e:
            logger.error(f"Failed to get transcript content for session {session_id}: {str(e)}")
            return f"Error retrieving transcript: {str(e)}"


def create_server() -> Server:
    """Create and configure the MCP server"""
    server = Server("meeting-transcription-agent")
    transcription_server = MeetingTranscriptionServer()
    
    @server.list_tools()
    async def list_tools() -> List[Tool]:
        """List available tools"""
        return [
            Tool(
                name="start_recording",
                description="Start a new meeting recording session with specified audio devices",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique identifier for the recording session"
                        },
                        "microphone_device": {
                            "type": "string",
                            "description": "Name or ID of the microphone device to use"
                        },
                        "speaker_device": {
                            "type": "string",
                            "description": "Name or ID of the speaker device to monitor"
                        }
                    },
                    "required": ["session_id", "microphone_device", "speaker_device"]
                }
            ),
            Tool(
                name="stop_recording",
                description="Stop a recording session and get the final transcript",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to stop"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_session_status",
                description="Get the current status of a recording session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to check"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="list_audio_devices",
                description="List all available audio input and output devices",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            Tool(
                name="start_client_recording",
                description="Start a client-side recording session that receives audio from the client",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique identifier for the recording session"
                        },
                        "sample_rate": {
                            "type": "integer",
                            "description": "Audio sample rate in Hz",
                            "default": 16000
                        },
                        "channels": {
                            "type": "integer",
                            "description": "Number of audio channels",
                            "default": 1
                        },
                        "chunk_duration": {
                            "type": "integer",
                            "description": "Duration of audio chunks for processing (seconds)",
                            "default": 5
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="send_audio_chunk",
                description="Send an audio chunk from the client to the server",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the recording session"
                        },
                        "audio_data": {
                            "type": "string",
                            "description": "Base64-encoded audio data"
                        },
                        "metadata": {
                            "type": "object",
                            "description": "Optional metadata about the audio chunk",
                            "properties": {
                                "timestamp": {"type": "number"},
                                "format": {"type": "string"},
                                "size": {"type": "integer"}
                            }
                        }
                    },
                    "required": ["session_id", "audio_data"]
                }
            ),
            Tool(
                name="stop_client_recording",
                description="Stop client recording and get the final transcript",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to stop"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_client_session_status",
                description="Get the current status of a client recording session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to check"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_audio_instructions",
                description="Get instructions for client-side audio capture",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "instruction_type": {
                            "type": "string",
                            "description": "Type of instructions to get",
                            "enum": ["web_audio", "desktop"],
                            "default": "web_audio"
                        }
                    }
                }
            ),
            Tool(
                name="export_transcript",
                description="Export a session transcript to a file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to export"
                        },
                        "format": {
                            "type": "string",
                            "description": "Export format",
                            "enum": ["json", "txt", "srt"],
                            "default": "json"
                        },
                        "file_path": {
                            "type": "string",
                            "description": "Optional file path (if not provided, auto-generated)"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="list_exported_transcripts",
                description="List all exported transcript files",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "exports_dir": {
                            "type": "string",
                            "description": "Directory to scan for exported files",
                            "default": "/tmp/transcripts"
                        }
                    }
                }
            ),
            Tool(
                name="get_device_selection_options",
                description="Get available audio devices for selection before starting recording",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session ID for the planned recording"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            Tool(
                name="get_transcript_content",
                description="Get transcript content formatted for opening in VS Code editor",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "ID of the session to get transcript for"
                        },
                        "format": {
                            "type": "string",
                            "description": "Format for the transcript content",
                            "enum": ["txt", "json", "srt", "markdown"],
                            "default": "txt"
                        },
                        "include_metadata": {
                            "type": "boolean",
                            "description": "Include metadata like timestamps and confidence scores",
                            "default": "false"
                        }
                    },
                    "required": ["session_id"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """Handle tool calls"""
        try:
            if name == "start_recording":
                session_id = arguments["session_id"]
                microphone_device = arguments.get("microphone_device")
                speaker_device = arguments.get("speaker_device")
                
                # Check if we need to provide device selection options
                if not microphone_device or not speaker_device:
                    device_options = await transcription_server.get_device_selection_options(session_id)
                    
                    missing_devices = []
                    if not microphone_device:
                        missing_devices.append("microphone_device")
                    if not speaker_device:
                        missing_devices.append("speaker_device")
                    
                    device_options['error'] = f"Missing required parameters: {', '.join(missing_devices)}"
                    device_options['message'] = "Please select devices from the available options below and call start_recording again with the selected device IDs."
                    
                    return [TextContent(type="text", text=json.dumps(device_options, indent=2))]
                
                # Both devices provided, proceed with recording
                result = await transcription_server.start_recording_session(session_id, arguments)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "stop_recording":
                result = await transcription_server.stop_recording_session(
                    arguments["session_id"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_session_status":
                result = await transcription_server.get_session_status(
                    arguments["session_id"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "list_audio_devices":
                result = await transcription_server.list_audio_devices()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "start_client_recording":
                result = transcription_server.start_client_recording(
                    arguments["session_id"],
                    arguments
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "send_audio_chunk":
                result = transcription_server.receive_audio_chunk(
                    arguments["session_id"],
                    arguments["audio_data"],
                    arguments.get("metadata")
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "stop_client_recording":
                result = await transcription_server.stop_client_recording(
                    arguments["session_id"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_client_session_status":
                result = transcription_server.get_client_session_status(
                    arguments["session_id"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_audio_instructions":
                instruction_type = arguments.get("instruction_type", "web_audio")
                result = transcription_server.get_audio_instructions(instruction_type)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "export_transcript":
                result = await transcription_server.export_transcript_to_file(
                    arguments["session_id"],
                    arguments.get("format", "json"),
                    arguments.get("file_path")
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "list_exported_transcripts":
                exports_dir = arguments.get("exports_dir", "/tmp/transcripts")
                result = await transcription_server.list_exported_transcripts(exports_dir)
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_device_selection_options":
                result = await transcription_server.get_device_selection_options(
                    arguments["session_id"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_transcript_content":
                result = await transcription_server.get_transcript_content_for_editor(
                    arguments["session_id"],
                    arguments.get("format", "txt"),
                    arguments.get("include_metadata", False)
                )
                return [TextContent(type="text", text=result)]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Error in tool {name}: {str(e)}")
            return [TextContent(
                type="text", 
                text=f"Error: {str(e)}"
            )]
    
    @server.list_resources()
    async def list_resources() -> List[Resource]:
        """List available resources"""
        return [
            Resource(
                uri="meeting://sessions/active",  # type: ignore
                name="Active Recording Sessions",
                description="List of currently active recording sessions",
                mimeType="application/json"
            ),
            Resource(
                uri="meeting://devices/audio",  # type: ignore
                name="Audio Devices",
                description="Available audio input and output devices",
                mimeType="application/json"
            )
        ]
    
    @server.read_resource()
    async def read_resource(uri: str) -> str:
        """Read resource content"""
        if uri == "meeting://sessions/active":
            active_sessions = {
                session_id: {
                    'status': session['status'],
                    'duration': asyncio.get_event_loop().time() - session['start_time'],
                    'config': session['config']
                }
                for session_id, session in transcription_server.active_sessions.items()
            }
            return json.dumps(active_sessions, indent=2)
        
        elif uri == "meeting://devices/audio":
            devices = await transcription_server.list_audio_devices()
            return json.dumps(devices, indent=2)
        
        else:
            raise ValueError(f"Unknown resource: {uri}")
    
    return server


async def main():
    """Main entry point"""
    # Initialize server
    server = create_server()
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())


if __name__ == "__main__":
    asyncio.run(main())