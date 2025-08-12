"""
Simple settings for fast-whisper MCP server
"""

import os
from typing import Any, Dict

class Settings:
    """Simple environment-based settings"""
    
    def __init__(self):
        self.settings = {
            'WHISPER_MODEL_SIZE': os.getenv('WHISPER_MODEL_SIZE', 'base'),
            'LOG_LEVEL': os.getenv('LOG_LEVEL', 'INFO'),
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """Get a setting value"""
        return self.settings.get(key, default)
    
    def to_dict(self) -> Dict[str, Any]:
        """Return all settings as dict"""
        return self.settings.copy()