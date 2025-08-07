"""
Configuration settings for the meeting transcription agent
"""

import os
from typing import Any, Dict, List

class Settings:
    """Configuration settings manager"""
    
    def __init__(self):
        """Initialize settings from environment variables"""
        self.config: Dict[str, Any] = {}
        self._load_environment_variables()
    
    def _load_environment_variables(self) -> None:
        """Load configuration from environment variables"""
        # Local Whisper settings
        self.config['WHISPER_MODEL_SIZE'] = os.getenv('WHISPER_MODEL_SIZE', 'base')
        
        # Ollama post-processing settings
        self.config['OLLAMA_URL'] = os.getenv('OLLAMA_URL')
        self.config['OLLAMA_MODEL'] = os.getenv('OLLAMA_MODEL', 'llama2')
        
        # Audio settings
        self.config['DEFAULT_SAMPLE_RATE'] = int(os.getenv('DEFAULT_SAMPLE_RATE', '16000'))
        self.config['DEFAULT_CHANNELS'] = int(os.getenv('DEFAULT_CHANNELS', '1'))
        self.config['DEFAULT_CHUNK_DURATION'] = int(os.getenv('DEFAULT_CHUNK_DURATION', '30'))
        
        # Server settings
        self.config['MAX_CONCURRENT_SESSIONS'] = int(os.getenv('MAX_CONCURRENT_SESSIONS', '5'))
        self.config['SESSION_TIMEOUT'] = int(os.getenv('SESSION_TIMEOUT', '3600'))  # 1 hour
        
        # Transcription settings
        self.config['DEFAULT_TRANSCRIPTION_PROVIDER'] = os.getenv('DEFAULT_TRANSCRIPTION_PROVIDER', 'whisper_local')
        self.config['TRANSCRIPTION_CONFIDENCE_THRESHOLD'] = float(os.getenv('TRANSCRIPTION_CONFIDENCE_THRESHOLD', '0.5'))
        
        # Docker and deployment settings
        self.config['MCP_GATEWAY_URL'] = os.getenv('MCP_GATEWAY_URL', 'http://192.168.50.20:9000')
        
        # Logging settings
        self.config['LOG_LEVEL'] = os.getenv('LOG_LEVEL', 'INFO')
        self.config['LOG_FILE'] = os.getenv('LOG_FILE', '/tmp/meeting-transcription.log')
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value"""
        return self.config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """Set a configuration value"""
        self.config[key] = value
    
    def has(self, key: str) -> bool:
        """Check if a configuration key exists"""
        return key in self.config
    
    def get_audio_config(self) -> Dict[str, Any]:
        """Get audio-related configuration"""
        return {
            'sample_rate': self.get('DEFAULT_SAMPLE_RATE'),
            'channels': self.get('DEFAULT_CHANNELS'),
            'chunk_duration': self.get('DEFAULT_CHUNK_DURATION')
        }
    
    def get_transcription_config(self) -> Dict[str, Any]:
        """Get transcription-related configuration"""
        return {
            'provider': self.get('DEFAULT_TRANSCRIPTION_PROVIDER'),
            'confidence_threshold': self.get('TRANSCRIPTION_CONFIDENCE_THRESHOLD'),
            'whisper_model_size': self.get('WHISPER_MODEL_SIZE'),
            'ollama_url': self.get('OLLAMA_URL'),
            'ollama_model': self.get('OLLAMA_MODEL')
        }
    
    def validate_required_settings(self) -> List[str]:
        """Validate that required settings are present"""
        errors: List[str] = []
        
        # Local Whisper is the primary transcription provider
        # No API keys required for basic functionality
        
        return errors
    
    def to_dict(self) -> Dict[str, Any]:
        """Return all settings as a dictionary"""
        return self.config.copy()
    
    def __repr__(self) -> str:
        """String representation of settings"""
        return f"Settings({self.config})"