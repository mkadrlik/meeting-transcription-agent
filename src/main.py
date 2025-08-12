#!/usr/bin/env python3
"""
Fast Whisper MCP Server - Simplified Implementation
"""

import asyncio
import base64
import json
import logging
from typing import Dict, Any, List, Union

from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import TextContent
import mcp.types as types

from transcription.service import MeetingTranscriptionService

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class MeetingTranscriptionAgentServer:
    """Simplified MCP server for fast whisper transcription"""
    
    def __init__(self):
        self.whisper_service = MeetingTranscriptionService()
        self.active_sessions: Dict[str, Dict[str, Any]] = {}
    
    def start_session(self, session_id: str) -> Dict[str, Any]:
        """Start a new transcription session"""
        if session_id in self.active_sessions:
            return {"error": f"Session {session_id} already exists"}
        
        self.active_sessions[session_id] = {
            "status": "active",
            "audio_chunks": [],
            "created": asyncio.get_event_loop().time()
        }
        
        logger.info(f"Started session: {session_id}")
        return {"success": True, "session_id": session_id, "status": "active"}
    
    def add_audio_chunk(self, session_id: str, audio_data: str) -> Dict[str, Any]:
        """Add audio chunk to session"""
        if session_id not in self.active_sessions:
            return {"error": f"Session {session_id} not found"}
        
        try:
            # Decode base64 audio data
            audio_bytes = base64.b64decode(audio_data)
            self.active_sessions[session_id]["audio_chunks"].append(audio_bytes)
            
            chunk_count = len(self.active_sessions[session_id]["audio_chunks"])
            logger.info(f"Added audio chunk to session {session_id} (total: {chunk_count})")
            
            return {"success": True, "chunk_count": chunk_count}
        except Exception as e:
            logger.error(f"Failed to add audio chunk: {e}")
            return {"error": str(e)}
    
    async def transcribe_session(self, session_id: str) -> Dict[str, Any]:
        """Transcribe all audio chunks in a session"""
        if session_id not in self.active_sessions:
            return {"error": f"Session {session_id} not found"}
        
        session = self.active_sessions[session_id]
        audio_chunks = session["audio_chunks"]
        
        if not audio_chunks:
            return {"error": "No audio data in session"}
        
        try:
            # Combine all audio chunks
            combined_audio = b''.join(audio_chunks)
            
            # Transcribe using FastWhisperService
            result = await self.whisper_service.transcribe_audio(session_id, combined_audio)
            
            # Clean up session
            del self.active_sessions[session_id]
            
            return result
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"error": str(e)}
    
    def get_session_status(self, session_id: str) -> Dict[str, Any]:
        """Get status of a session"""
        if session_id not in self.active_sessions:
            return {"error": f"Session {session_id} not found"}
        
        session = self.active_sessions[session_id]
        return {
            "session_id": session_id,
            "status": session["status"],
            "chunk_count": len(session["audio_chunks"]),
            "created": session["created"]
        }

def create_server() -> Server:
    """Create and configure the MCP server"""
    server = Server("fast-whisper-transcription")
    whisper_server = MeetingTranscriptionAgentServer()
    
    @server.list_tools()
    async def list_tools() -> List[types.Tool]:
        """List available tools"""
        return [
            types.Tool(
                name="start_session",
                description="Start a new transcription session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Unique identifier for the session"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            types.Tool(
                name="add_audio_chunk",
                description="Add base64-encoded audio chunk to session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session identifier"
                        },
                        "audio_data": {
                            "type": "string",
                            "description": "Base64-encoded audio data"
                        }
                    },
                    "required": ["session_id", "audio_data"]
                }
            ),
            types.Tool(
                name="transcribe_session",
                description="Transcribe all audio in session and save to file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session identifier"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            types.Tool(
                name="get_session_status",
                description="Get status of a transcription session",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "session_id": {
                            "type": "string",
                            "description": "Session identifier"
                        }
                    },
                    "required": ["session_id"]
                }
            ),
            types.Tool(
                name="list_transcriptions",
                description="List all saved transcription files",
                inputSchema={
                    "type": "object",
                    "properties": {}
                }
            ),
            types.Tool(
                name="get_transcription",
                description="Get content of a specific transcription file",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filename": {
                            "type": "string",
                            "description": "Name of the transcription file"
                        }
                    },
                    "required": ["filename"]
                }
            )
        ]
    
    @server.call_tool()
    async def call_tool(name: str, arguments: Dict[str, Any]) -> List[Union[types.TextContent, types.ImageContent, types.EmbeddedResource]]:
        """Handle tool calls"""
        try:
            if name == "start_session":
                result = whisper_server.start_session(arguments["session_id"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "add_audio_chunk":
                result = whisper_server.add_audio_chunk(
                    arguments["session_id"],
                    arguments["audio_data"]
                )
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "transcribe_session":
                result = await whisper_server.transcribe_session(arguments["session_id"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_session_status":
                result = whisper_server.get_session_status(arguments["session_id"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "list_transcriptions":
                result = whisper_server.whisper_service.list_transcriptions()
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            elif name == "get_transcription":
                result = whisper_server.whisper_service.get_transcription(arguments["filename"])
                return [TextContent(type="text", text=json.dumps(result, indent=2))]
            
            else:
                raise ValueError(f"Unknown tool: {name}")
                
        except Exception as e:
            logger.error(f"Error in tool {name}: {e}")
            return [TextContent(type="text", text=f"Error: {str(e)}")]
    
    return server

async def main():
    """Main entry point"""
    logger.info("Starting Meeting Transcription Agent MCP Server...")
    
    # Initialize server
    server = create_server()
    
    # Run server with stdio transport
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, server.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())