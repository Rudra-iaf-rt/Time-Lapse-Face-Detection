# quick_test.py
"""Quick validation script for Phase 1."""

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import numpy as np
from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator
from reid.reid_gallery import ReIDGallery

def quick_test():
    """Run a quick validation test."""
    print("🧪 Quick Validation Test")
    print("-" * 40)
    
    try:
        # 1. Test OSNet
        print("1. Testing OSNet...")
        extractor = OSNetReIDExtractor()
        test_img = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
        emb = extractor.extract_embedding(test_img)
        assert emb.shape == (512,), "Wrong embedding shape"
        assert abs(np.linalg.norm(emb) - 1.0) < 0.001, "Not normalized"
        print("   ✅ OSNet works")
        
        # 2. Test Quality
        print("2. Testing Quality Estimator...")
        estimator = QualityEstimator()
        quality = estimator.estimate_quality(test_img)
        assert 0 <= quality['overall'] <= 1, "Quality score out of range"
        print(f"   ✅ Quality Estimator works (score: {quality['overall']:.3f})")
        
        # 3. Test Gallery
        print("3. Testing Gallery...")
        gallery = ReIDGallery("tests/test_data/quick_test.db")
        emb2 = np.random.randn(512)
        emb2 = emb2 / np.linalg.norm(emb2)
        import datetime
        gid = gallery.add_observation(0, "TEST", emb, 0.8, datetime.datetime.now())
        gid2 = gallery.add_observation(1, "TEST2", emb2, 0.7, datetime.datetime.now())
        assert gid != gid2, "Different people matched"
        print(f"   ✅ Gallery works (created {gid} and {gid2})")
        
        print("-" * 40)
        print("✅ All components working!")
        return True
        
    except Exception as e:
        print(f"❌ Test failed: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    quick_test()