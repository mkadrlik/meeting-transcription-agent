#!/usr/bin/env python3
"""
Simple test for Fast Whisper MCP Server
"""

import logging
from faster_whisper import WhisperModel

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_faster_whisper():
    """Test that faster-whisper works"""
    try:
        logger.info("Testing faster-whisper...")
        model = WhisperModel("base", device="cpu", compute_type="int8")
        logger.info("✅ Fast Whisper model loaded successfully")
        return True
    except Exception as e:
        logger.error(f"❌ Fast Whisper test failed: {e}")
        return False

if __name__ == "__main__":
    success = test_faster_whisper()
    exit(0 if success else 1)