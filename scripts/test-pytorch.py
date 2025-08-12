#!/usr/bin/env python3
"""
Test script to verify PyTorch works without ARM64 issues
"""

import os
import sys
import logging

# Set environment variables before importing PyTorch
os.environ['PYTORCH_DISABLE_CUDNN_WARNINGS'] = '1'
os.environ['OMP_NUM_THREADS'] = '1'
os.environ['MKL_NUM_THREADS'] = '1'
os.environ['OPENBLAS_NUM_THREADS'] = '1'
os.environ['VECLIB_MAXIMUM_THREADS'] = '1'
os.environ['NUMEXPR_NUM_THREADS'] = '1'

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def test_pytorch():
    """Test PyTorch import and basic functionality"""
    try:
        logger.info("Testing PyTorch import...")
        import torch
        logger.info(f"✅ PyTorch version: {torch.__version__}")
        
        # Test basic tensor operations
        logger.info("Testing tensor operations...")
        x = torch.randn(2, 3)
        y = torch.randn(3, 2)
        z = torch.mm(x, y)
        logger.info(f"✅ Tensor operations work: {z.shape}")
        
        # Check if CUDA is available (should be False for CPU-only)
        logger.info(f"CUDA available: {torch.cuda.is_available()}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ PyTorch test failed: {e}")
        return False

def test_whisper_import():
    """Test Whisper import"""
    try:
        logger.info("Testing Whisper import...")
        import whisper
        logger.info("✅ Whisper imported successfully")
        
        # Test model loading (just check if it doesn't crash)
        logger.info("Testing model loading...")
        available_models = whisper.available_models()
        logger.info(f"✅ Available models: {available_models}")
        
        return True
        
    except Exception as e:
        logger.error(f"❌ Whisper test failed: {e}")
        return False

def main():
    """Main test function"""
    logger.info("🧪 Testing PyTorch and Whisper compatibility...")
    
    pytorch_ok = test_pytorch()
    whisper_ok = test_whisper_import()
    
    if pytorch_ok and whisper_ok:
        logger.info("✅ All tests passed!")
        sys.exit(0)
    else:
        logger.error("❌ Some tests failed")
        sys.exit(1)

if __name__ == "__main__":
    main()