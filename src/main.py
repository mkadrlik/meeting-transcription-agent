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
import sys
from typing import Optional, Dict, Any, List

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Resource, Tool, TextContent, ImageContent, EmbeddedResource
import mcp.server.session
import mcp.types as types

from .audio.capture import AudioCapture
from .transcription.service import TranscriptionService
from .config.settings import Settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeetingTranscriptionServer:
    def __init__(self):
        self.settings = Settings()
        self.audio_capture = AudioCapture(self.settings)
        self.transcription_service = TranscriptionService(self.settings)
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
        
    async def start_recording_session(self, session_id: str, audio_config: Dict[str, Any]) -> Dict[str, Any]:
        """Start a new recording session"""
        try:
            # Validate audio configuration
            microphone_device = audio_config.get('microphone_device')
            speaker_device = audio_config.get('speaker_device', 'default')
            
            if not microphone_device:
                raise ValueError("Microphone device must be specified")
            
            # Initialize audio capture for this session
            session_config = {
                'session_id': session_id,
                'microphone_device': microphone_device,
                'speaker_device': speaker_device,
                'sample_rate': audio_config.get('sample_rate', 16000),
                'channels': audio_config.get('channels', 1),
                'chunk_duration': audio_config.get('chunk_duration', 30)  # seconds
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
    
    async def list_audio_devices(self) -> Dict[str, List[Dict[str, Any]]]:
        """List available audio input and output devices"""
        return await self.audio_capture.list_devices()


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
                            "description": "Name or ID of the speaker device to monitor (optional)",
                            "default": "default"
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
                            "default": 30
                        }
                    },
                    "required": ["session_id", "microphone_device"]
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
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[types.TextContent | types.ImageContent | types.EmbeddedResource]:
        """Handle tool calls"""
        try:
            if name == "start_recording":
                result = await transcription_server.start_recording_session(
                    arguments["session_id"],
                    arguments
                )
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
                uri="meeting://sessions/active",
                name="Active Recording Sessions",
                description="List of currently active recording sessions",
                mimeType="application/json"
            ),
            Resource(
                uri="meeting://devices/audio",
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