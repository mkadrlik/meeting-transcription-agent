"""
Simple audio client instructions for fast-whisper MCP server
"""

from typing import Dict, Any

class AudioInstructions:
    """Provides simple instructions for client-side audio capture"""
    
    @staticmethod
    def get_web_audio_instructions() -> Dict[str, Any]:
        """Get instructions for web-based audio capture"""
        return {
            "type": "web_audio_api",
            "instructions": {
                "1_request_permission": "navigator.mediaDevices.getUserMedia({audio: true})",
                "2_create_recorder": "Use MediaRecorder API",
                "3_capture_audio": "Record complete audio session",
                "4_encode": "Convert to base64",
                "5_send_via_mcp": "Use MCP tools: start_session -> add_audio_chunk -> transcribe_session"
            },
            "sample_code": {
                "javascript": """
// Simple audio recording for Fast Whisper MCP
async function recordAndTranscribe(sessionId) {
    // Start MCP session
    await mcpClient.callTool('start_session', {session_id: sessionId});
    
    // Get audio stream
    const stream = await navigator.mediaDevices.getUserMedia({audio: true});
    const recorder = new MediaRecorder(stream);
    const chunks = [];
    
    recorder.ondataavailable = (event) => chunks.push(event.data);
    
    recorder.onstop = async () => {
        const blob = new Blob(chunks, {type: 'audio/wav'});
        const arrayBuffer = await blob.arrayBuffer();
        const base64 = btoa(String.fromCharCode(...new Uint8Array(arrayBuffer)));
        
        // Send audio to MCP server
        await mcpClient.callTool('add_audio_chunk', {
            session_id: sessionId,
            audio_data: base64
        });
        
        // Transcribe
        const result = await mcpClient.callTool('transcribe_session', {
            session_id: sessionId
        });
        
        console.log('Transcription:', result);
    };
    
    recorder.start();
    // Stop recording after some time or user action
    setTimeout(() => recorder.stop(), 10000);
}
"""
            }
        }
    
    @staticmethod
    def get_desktop_audio_instructions() -> Dict[str, Any]:
        """Get instructions for desktop application audio capture"""
        return {
            "type": "desktop_application",
            "instructions": {
                "1_capture_audio": "Record audio using your preferred method",
                "2_encode": "Convert to base64",
                "3_send_via_mcp": "Use MCP tools in sequence"
            },
            "workflow": [
                "start_session(session_id)",
                "add_audio_chunk(session_id, base64_audio)",
                "transcribe_session(session_id)",
                "get_transcription(filename) # to retrieve saved file"
            ]
        }