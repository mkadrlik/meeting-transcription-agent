#!/usr/bin/env python3
"""
Test script to verify Whisper model is working correctly
"""

import os
import sys
import logging
import numpy as np

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_whisper_model():
    """Test that Whisper model loads and works"""
    try:
        import whisper
        
        model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')
        logger.info(f"Testing Whisper model: {model_size}")
        
        # Load model
        model = whisper.load_model(model_size)
        logger.info("✅ Model loaded successfully")
        
        # Test with minimal audio (1 second of silence)
        test_audio = np.zeros(16000, dtype=np.float32)
        result = model.transcribe(test_audio)
        
        logger.info("✅ Model transcription test completed")
        logger.info(f"Test result: '{result.get('text', '').strip()}'")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Whisper test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_whisper_model()
    sys.exit(0 if success else 1)