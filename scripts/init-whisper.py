#!/usr/bin/env python3
"""
Whisper Model Initialization Script

Pre-downloads and caches the Whisper model during container startup
to ensure it's available when the MCP server starts.
"""

import os
import sys
import logging
from pathlib import Path

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def ensure_whisper_model():
    """Ensure Whisper model is downloaded and cached"""
    try:
        # Set environment variables to prevent PyTorch issues
        os.environ['PYTORCH_DISABLE_CUDNN_WARNINGS'] = '1'
        os.environ['OMP_NUM_THREADS'] = '1'
        os.environ['MKL_NUM_THREADS'] = '1'
        os.environ['OPENBLAS_NUM_THREADS'] = '1'
        os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
        os.environ['NUMEXPR_NUM_THREADS'] = '1'
        
        import whisper
        
        # Get model size from environment
        model_size = os.getenv('WHISPER_MODEL_SIZE', 'base')
        
        # Set up cache directories
        cache_dir = Path('/app/.cache')
        whisper_cache = cache_dir / 'whisper'
        torch_cache = cache_dir / 'torch'
        
        # Create cache directories
        cache_dir.mkdir(parents=True, exist_ok=True)
        whisper_cache.mkdir(parents=True, exist_ok=True)
        torch_cache.mkdir(parents=True, exist_ok=True)
        
        # Set environment variables for caching
        os.environ['WHISPER_CACHE_DIR'] = str(whisper_cache)
        os.environ['TORCH_HOME'] = str(torch_cache)
        
        logger.info(f"Initializing Whisper model: {model_size}")
        logger.info(f"Cache directory: {whisper_cache}")
        logger.info(f"PyTorch cache: {torch_cache}")
        
        # Load model (this will download it if not cached)
        logger.info("Loading Whisper model...")
        model = whisper.load_model(model_size)
        
        logger.info(f"Successfully initialized Whisper model: {model_size}")
        logger.info(f"Model cached in: {whisper_cache}")
        
        # Verify model works with a simple test
        logger.info("Testing model with minimal audio...")
        import numpy as np
        
        # Create minimal test audio (1 second of silence)
        test_audio = np.zeros(16000, dtype=np.float32)
        
        # Test transcription with error handling
        try:
            result = model.transcribe(test_audio)
            logger.info("Model test completed successfully")
        except Exception as e:
            logger.warning(f"Model test had issues but model loaded: {e}")
        
        logger.info(f"Cache contents: {list(whisper_cache.glob('*'))}")
        
        return True
        
    except ImportError as e:
        logger.error(f"Whisper library not available: {e}")
        return False
    except Exception as e:
        logger.error(f"Failed to initialize Whisper model: {e}")
        logger.error(f"Error details: {type(e).__name__}: {str(e)}")
        return False

def main():
    """Main initialization function"""
    logger.info("Starting Whisper model initialization...")
    
    # Try multiple times with different approaches
    for attempt in range(3):
        logger.info(f"Attempt {attempt + 1}/3")
        
        success = ensure_whisper_model()
        
        if success:
            logger.info("Whisper model initialization completed successfully")
            sys.exit(0)
        else:
            if attempt < 2:
                logger.warning(f"Attempt {attempt + 1} failed, retrying...")
                import time
                time.sleep(2)
            else:
                logger.error("All attempts failed")
    
    # If we're in a build environment, don't fail the build
    if os.getenv('DOCKER_BUILDKIT') or os.getenv('BUILDX_BUILDER'):
        logger.warning("Build environment detected, allowing failure for runtime retry")
        sys.exit(0)
    else:
        logger.error("Whisper model initialization failed")
        sys.exit(1)

if __name__ == "__main__":
    main()