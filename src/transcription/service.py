"""
Transcription service module for meeting transcription

Handles speech-to-text conversion using various transcription providers.
"""

import asyncio
import json
import logging
import time
from typing import Dict, List, Any, Optional, AsyncGenerator

try:
    import whisper
    WHISPER_LOCAL_AVAILABLE = True
except ImportError:
    WHISPER_LOCAL_AVAILABLE = False
    whisper = None

try:
    import requests
    REQUESTS_AVAILABLE = True
except ImportError:
    REQUESTS_AVAILABLE = False
    requests = None

logger = logging.getLogger(__name__)

class TranscriptionResult:
    """Represents a transcription result"""
    
    def __init__(self, text: str, confidence: float = 0.0, timestamp: Optional[float] = None,
                 speaker_id: Optional[str] = None):
        self.text = text
        self.confidence = confidence
        self.timestamp = timestamp or time.time()
        self.speaker_id = speaker_id
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            'text': self.text,
            'confidence': self.confidence,
            'timestamp': self.timestamp,
            'speaker_id': self.speaker_id
        }

class TranscriptionProvider:
    """Base class for transcription providers"""
    
    async def transcribe_audio(self, audio_data: bytes, session_config: Dict[str, Any]) -> TranscriptionResult:
        """Transcribe audio data to text"""
        raise NotImplementedError
    
    async def transcribe_stream(self, audio_stream: AsyncGenerator[bytes, None], 
                              session_config: Dict[str, Any]) -> AsyncGenerator[TranscriptionResult, None]:
        """Transcribe streaming audio data"""
        raise NotImplementedError


class LocalWhisperProvider(TranscriptionProvider):
    """Local Whisper transcription provider using CPU-only processing"""
    
    def __init__(self, model_size: str = "base"):
        if not WHISPER_LOCAL_AVAILABLE:
            raise RuntimeError("Whisper library not available")

        self.model_size = model_size
        self.model: Optional[Any] = None
        self._load_model()
    
    def _load_model(self) -> None:
        """Load the Whisper model"""
        try:
            if whisper is not None:
                logger.info(f"Loading Whisper model: {self.model_size}")
                self.model = whisper.load_model(self.model_size)
                logger.info(f"Successfully loaded Whisper model: {self.model_size}")
            else:
                raise RuntimeError("Whisper module not available")
        except Exception as e:
            logger.error(f"Failed to load Whisper model: {str(e)}")
            raise
    
    def _prepare_audio_for_whisper(self, audio_data: bytes, sample_rate: int = 16000) -> str:
        """Prepare audio data for Whisper processing"""
        import tempfile
        import wave
        import os
        from typing import cast, Any
        
        if not audio_data:
            raise ValueError("Audio data cannot be empty")
        
        if sample_rate <= 0:
            raise ValueError("Sample rate must be positive")
        
        # Create temporary file
        with tempfile.NamedTemporaryFile(suffix=".wav", delete=False) as f:
            temp_path = f.name
        
        try:
            # Write WAV file - when opened with 'wb', wave.open returns a Wave_write object
            wav_writer = wave.open(temp_path, 'wb')
            # Cast to Any to avoid type checker issues with Wave_write methods
            wav_writer = cast(Any, wav_writer)
            
            try:
                wav_writer.setnchannels(1)  # Set to mono
                wav_writer.setsampwidth(2)  # 16-bit audio (2 bytes per sample)
                wav_writer.setframerate(sample_rate)  # Set sample rate
                wav_writer.writeframes(audio_data)
            finally:
                wav_writer.close()
                
        except Exception as e:
            # Clean up temp file if writing failed
            try:
                os.unlink(temp_path)
            except Exception:
                pass
            raise RuntimeError(f"Failed to create WAV file: {str(e)}") from e
        
        return temp_path
    
    async def transcribe_audio(self, audio_data: bytes, session_config: Dict[str, Any]) -> TranscriptionResult:
        """Transcribe audio using local Whisper model"""
        try:
            if not self.model:
                raise RuntimeError("Whisper model not loaded")
            
            if not audio_data:
                logger.warning("Empty audio data provided for transcription")
                return TranscriptionResult(text="", confidence=0.0)
            
            sample_rate = session_config.get('sample_rate', 16000)
            
            # Validate sample rate
            if sample_rate <= 0:
                logger.warning(f"Invalid sample rate {sample_rate}, using default 16000")
                sample_rate = 16000
            
            # Prepare audio file
            audio_file = self._prepare_audio_for_whisper(audio_data, sample_rate)
            
            try:
                # Transcribe with Whisper
                result = await asyncio.to_thread(self.model.transcribe, audio_file)
                
                text = result.get("text", "").strip()
                confidence = 0.9  # Whisper doesn't provide confidence scores directly
                
                return TranscriptionResult(
                    text=text,
                    confidence=confidence,
                    timestamp=time.time()
                )
                
            finally:
                # Clean up temporary file
                import os
                try:
                    os.unlink(audio_file)
                except Exception as e:
                    logger.debug(f"Failed to clean up temp file {audio_file}: {str(e)}")
                    
        except Exception as e:
            logger.error(f"Local Whisper transcription error: {str(e)}")
            return TranscriptionResult(
                text=f"[Local Whisper Error: {str(e)}]",
                confidence=0.0
            )

class OllamaPostProcessor:
    """Post-processor for cleaning and enhancing transcripts using Ollama"""
    
    def __init__(self, ollama_url: str, model_name: str = "llama2"):
        if not REQUESTS_AVAILABLE:
            raise RuntimeError("Requests library not available for Ollama integration")
        
        self.ollama_url = ollama_url.rstrip('/')
        self.model_name = model_name
    
    async def post_process_transcript(self, raw_transcript: str) -> str:
        """Send transcript to Ollama for cleaning and formatting"""
        try:
            prompt = f"""Please clean up and format this meeting transcript. Fix any obvious transcription errors, add proper punctuation, and organize it clearly while maintaining the original meaning:

{raw_transcript}

Cleaned transcript:"""
            
            payload = {
                "model": self.model_name,
                "prompt": prompt,
                "stream": False,
                "options": {
                    "temperature": 0.1,
                    "top_p": 0.9,
                    "max_tokens": 2000
                }
            }
            
            if requests is not None:
                response = await asyncio.to_thread(
                    requests.post,
                    f"{self.ollama_url}/api/generate",
                    json=payload,
                    timeout=30
                )
            else:
                raise RuntimeError("Requests module not available")
            
            if response.status_code == 200:
                result = response.json()
                cleaned_text = result.get("response", raw_transcript).strip()
                return cleaned_text
            else:
                logger.warning(f"Ollama post-processing failed: {response.status_code}")
                return raw_transcript
                
        except Exception as e:
            logger.error(f"Ollama post-processing error: {str(e)}")
            return raw_transcript



class TranscriptionService:
    """Main transcription service that manages providers and sessions"""
    
    def __init__(self, settings):
        self.settings = settings
        self.providers: Dict[str, TranscriptionProvider] = {}
        self.session_transcripts: Dict[str, List[TranscriptionResult]] = {}
        self.ollama_post_processor: Optional[OllamaPostProcessor] = None
        
        self._initialize_providers()
        self._initialize_post_processor()
    
    def _initialize_providers(self) -> None:
        """Initialize available transcription providers"""
        # Initialize Local Whisper provider (required)
        if not WHISPER_LOCAL_AVAILABLE:
            raise RuntimeError("Whisper library is required but not available. Please install openai-whisper.")
        
        try:
            whisper_model = self.settings.get('WHISPER_MODEL_SIZE', 'base')
            self.providers['whisper_local'] = LocalWhisperProvider(whisper_model)
            logger.info(f"Local Whisper provider initialized with model: {whisper_model}")
        except Exception as e:
            logger.error(f"Failed to initialize Local Whisper provider: {str(e)}")
            raise RuntimeError(f"Whisper provider initialization failed: {str(e)}")
        
        if not self.providers:
            raise RuntimeError("No transcription providers available")
    
    def _initialize_post_processor(self) -> None:
        """Initialize Ollama post-processor if configured"""
        ollama_url = self.settings.get('OLLAMA_URL')
        ollama_model = self.settings.get('OLLAMA_MODEL', 'llama2')
        
        if ollama_url and REQUESTS_AVAILABLE:
            try:
                self.ollama_post_processor = OllamaPostProcessor(ollama_url, ollama_model)
                logger.info(f"Ollama post-processor initialized: {ollama_url} with model {ollama_model}")
            except Exception as e:
                logger.warning(f"Failed to initialize Ollama post-processor: {str(e)}")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names"""
        return list(self.providers.keys())
    
    def get_default_provider(self) -> str:
        """Get the default/best available provider"""
        return 'whisper_local'
    
    async def transcribe_audio_chunk(self, session_id: str, audio_data: bytes, 
                                   session_config: Dict[str, Any]) -> TranscriptionResult:
        """Transcribe a single audio chunk"""
        if not audio_data:
            return TranscriptionResult("", 0.0)
        
        # Get provider to use
        provider_name = session_config.get('transcription_provider', self.get_default_provider())
        
        if provider_name not in self.providers:
            logger.warning(f"Provider {provider_name} not available, using default")
            provider_name = self.get_default_provider()
        
        provider = self.providers[provider_name]
        
        # Perform transcription
        result = await provider.transcribe_audio(audio_data, session_config)
        
        # Store result for session
        if session_id not in self.session_transcripts:
            self.session_transcripts[session_id] = []
        
        self.session_transcripts[session_id].append(result)
        
        logger.debug(f"Transcribed chunk for session {session_id}: {result.text[:50]}...")
        return result
    
    async def get_session_transcript(self, session_id: str) -> List[Dict[str, Any]]:
        """Get current transcript for a session"""
        if session_id not in self.session_transcripts:
            return []
        
        return [result.to_dict() for result in self.session_transcripts[session_id]]
    
    async def get_final_transcript(self, session_id: str) -> Dict[str, Any]:
        """Get final processed transcript for a session"""
        transcript_results = self.session_transcripts.get(session_id, [])
        
        if not transcript_results:
            return {
                'full_text': '',
                'segments': [],
                'word_count': 0,
                'duration': 0,
                'confidence_average': 0.0,
                'post_processed': False
            }
        
        # Combine all text segments
        full_text = ' '.join(result.text for result in transcript_results if result.text.strip())
        
        # Post-process with Ollama if available
        post_processed = False
        if self.ollama_post_processor and full_text:
            try:
                processed_text = await self.ollama_post_processor.post_process_transcript(full_text)
                if processed_text != full_text:
                    full_text = processed_text
                    post_processed = True
                    logger.info(f"Transcript post-processed with Ollama for session {session_id}")
            except Exception as e:
                logger.error(f"Ollama post-processing failed for session {session_id}: {str(e)}")
        
        # Calculate statistics
        word_count = len(full_text.split()) if full_text else 0
        
        start_time = min(result.timestamp for result in transcript_results)
        end_time = max(result.timestamp for result in transcript_results)
        duration = end_time - start_time
        
        valid_confidences = [r.confidence for r in transcript_results if r.confidence > 0]
        confidence_average = sum(valid_confidences) / len(valid_confidences) if valid_confidences else 0.0
        
        return {
            'full_text': full_text,
            'segments': [result.to_dict() for result in transcript_results],
            'word_count': word_count,
            'duration': duration,
            'confidence_average': confidence_average,
            'post_processed': post_processed,
            'provider': getattr(transcript_results[0], 'provider', 'unknown') if transcript_results else 'unknown'
        }
    
    async def clear_session_transcript(self, session_id: str) -> None:
        """Clear transcript data for a session"""
        if session_id in self.session_transcripts:
            del self.session_transcripts[session_id]
            logger.info(f"Cleared transcript data for session {session_id}")
    
    async def export_transcript(self, session_id: str, format: str = 'json') -> str:
        """Export transcript in specified format"""
        final_transcript = await self.get_final_transcript(session_id)
        
        if format.lower() == 'json':
            return json.dumps(final_transcript, indent=2)
        
        elif format.lower() == 'txt':
            return final_transcript['full_text']
        
        elif format.lower() == 'srt':
            # Generate SRT subtitle format
            segments = final_transcript['segments']
            srt_content = []
            
            for i, segment in enumerate(segments, 1):
                start_time = segment['timestamp']
                end_time = segment.get('end_timestamp', start_time + 3)  # Default 3-second segments
                
                # Format timestamps for SRT
                start_srt = self._format_srt_timestamp(start_time)
                end_srt = self._format_srt_timestamp(end_time)
                
                srt_content.append(f"{i}")
                srt_content.append(f"{start_srt} --> {end_srt}")
                srt_content.append(segment['text'])
                srt_content.append("")  # Empty line between entries
            
            return '\n'.join(srt_content)
        
        else:
            raise ValueError(f"Unsupported export format: {format}")
    
    def _format_srt_timestamp(self, timestamp: float) -> str:
        """Format timestamp for SRT format"""
        hours = int(timestamp // 3600)
        minutes = int((timestamp % 3600) // 60)
        seconds = int(timestamp % 60)
        milliseconds = int((timestamp % 1) * 1000)
        
        return f"{hours:02d}:{minutes:02d}:{seconds:02d},{milliseconds:03d}"