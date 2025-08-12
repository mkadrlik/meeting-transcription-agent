"""
Fast Whisper transcription service - simplified implementation
"""

import asyncio
import json
import logging
import os
import tempfile
import time
from pathlib import Path
from typing import Dict, Any, Optional

from faster_whisper import WhisperModel

logger = logging.getLogger(__name__)

class MeetingTranscriptionService:
    """Simplified transcription service using faster-whisper"""
    
    def __init__(self):
        self.model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')
        self.model: Optional[WhisperModel] = None
        # Try host-mounted directory first, then fall back to internal directory
        self._setup_transcriptions_dir()
        self._load_model()
    
    def _setup_transcriptions_dir(self) -> None:
        """Setup transcriptions directory, trying host-mounted first, then internal fallback"""
        # Try host-mounted directory first
        host_dir = Path('/app/host-data/transcriptions')
        if self._try_directory(host_dir):
            self.transcriptions_dir = host_dir
            logger.info(f"Using host-mounted transcriptions directory: {self.transcriptions_dir}")
            return
            
        # Fall back to internal directory
        internal_dir = Path('/app/data/transcriptions')
        if self._try_directory(internal_dir):
            self.transcriptions_dir = internal_dir
            logger.info(f"Using internal transcriptions directory: {self.transcriptions_dir}")
            return
            
        # Last resort: temporary directory
        import tempfile
        self.transcriptions_dir = Path(tempfile.mkdtemp(prefix="transcriptions_"))
        logger.warning(f"Using temporary directory: {self.transcriptions_dir}")
        logger.warning("Host directory permissions issue - transcriptions will not persist")
    
    def _try_directory(self, directory: Path) -> bool:
        """Try to create and write to a directory, return True if successful"""
        try:
            directory.mkdir(parents=True, exist_ok=True)
            test_file = directory / ".write_test"
            test_file.write_text("test")
            test_file.unlink()
            return True
        except (PermissionError, OSError):
            return False
        except Exception as e:
            logger.error(f"Unexpected error testing directory {directory}: {e}")
            return False
    
    def _load_model(self) -> None:
        """Load the faster-whisper model"""
        try:
            logger.info(f"Loading faster-whisper model: {self.model_size}")
            self.model = WhisperModel(
                self.model_size,
                device="cpu",
                compute_type="int8"  # Optimized for CPU
            )
            logger.info(f"Successfully loaded faster-whisper model: {self.model_size}")
        except Exception as e:
            logger.error(f"Failed to load faster-whisper model: {e}")
            raise
    
    async def transcribe_audio(self, session_id: str, audio_data: bytes) -> Dict[str, Any]:
        """Transcribe audio data and save to file"""
        if not audio_data:
            return {"error": "No audio data provided"}
        
        try:
            # Create temporary audio file
            with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as temp_file:
                temp_file.write(audio_data)
                temp_path = temp_file.name
            
            try:
                # Transcribe using faster-whisper
                segments, info = await asyncio.to_thread(
                    self.model.transcribe,
                    temp_path,
                    beam_size=5
                )
                
                # Collect segments
                transcript_segments = []
                full_text = []
                
                for segment in segments:
                    segment_data = {
                        "start": segment.start,
                        "end": segment.end,
                        "text": segment.text.strip(),
                        "confidence": getattr(segment, 'avg_logprob', 0.0)
                    }
                    transcript_segments.append(segment_data)
                    full_text.append(segment.text.strip())
                
                # Create transcript data
                transcript = {
                    "session_id": session_id,
                    "timestamp": time.time(),
                    "language": info.language,
                    "language_probability": info.language_probability,
                    "duration": info.duration,
                    "full_text": " ".join(full_text),
                    "segments": transcript_segments,
                    "word_count": len(" ".join(full_text).split())
                }
                
                # Save to file
                output_file = self.transcriptions_dir / f"{session_id}_{int(time.time())}.json"
                with open(output_file, 'w', encoding='utf-8') as f:
                    json.dump(transcript, f, indent=2, ensure_ascii=False)
                
                logger.info(f"Transcription saved: {output_file}")
                
                return {
                    "success": True,
                    "transcript": transcript,
                    "output_file": str(output_file)
                }
                
            finally:
                # Clean up temp file
                try:
                    os.unlink(temp_path)
                except Exception:
                    pass
                    
        except Exception as e:
            logger.error(f"Transcription failed: {e}")
            return {"error": str(e)}
    
    def list_transcriptions(self) -> Dict[str, Any]:
        """List all transcription files"""
        try:
            files = []
            for file_path in self.transcriptions_dir.glob("*.json"):
                stat = file_path.stat()
                files.append({
                    "filename": file_path.name,
                    "path": str(file_path),
                    "size": stat.st_size,
                    "created": stat.st_ctime,
                    "modified": stat.st_mtime
                })
            
            files.sort(key=lambda x: x['created'], reverse=True)
            
            return {
                "transcriptions_dir": str(self.transcriptions_dir),
                "files": files,
                "total_files": len(files)
            }
        except Exception as e:
            logger.error(f"Failed to list transcriptions: {e}")
            return {"error": str(e)}
    
    def get_transcription(self, filename: str) -> Dict[str, Any]:
        """Get a specific transcription file"""
        try:
            file_path = self.transcriptions_dir / filename
            if not file_path.exists():
                return {"error": "File not found"}
            
            with open(file_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.error(f"Failed to read transcription: {e}")
            return {"error": str(e)}