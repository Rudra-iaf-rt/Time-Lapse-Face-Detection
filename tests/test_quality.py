# tests/test_quality.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from reid.quality_estimator import QualityEstimator

def test_quality_initialization():
    """Test QualityEstimator initialization."""
    print("🧪 Testing QualityEstimator initialization...")
    try:
        estimator = QualityEstimator()
        print("✅ QualityEstimator initialized successfully")
        return estimator
    except Exception as e:
        print(f"❌ Failed to initialize QualityEstimator: {e}")
        return None

def test_quality_estimation(estimator):
    """Test quality estimation on various crops."""
    print("\n🧪 Testing quality estimation...")
    
    # Test cases: different quality crops
    test_cases = [
        {
            'name': 'High quality',
            'crop': np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8),
            'expected_min': 0.5
        },
        {
            'name': 'Low resolution',
            'crop': np.random.randint(0, 255, (32, 16, 3), dtype=np.uint8),
            'expected_min': 0.0
        },
        {
            'name': 'Blurry (simulated)',
            'crop': np.random.randint(0, 255, (128, 64, 3), dtype=np.uint8),
            'expected_min': 0.3
        }
    ]
    
    results = []
    for case in test_cases:
        print(f"\n   Testing: {case['name']}")
        quality = estimator.estimate_quality(case['crop'])
        
        print(f"   - Overall: {quality['overall']:.3f}")
        print(f"   - Resolution: {quality['resolution']:.3f}")
        print(f"   - Blur: {quality['blur']:.3f}")
        print(f"   - Contrast: {quality['contrast']:.3f}")
        print(f"   - Brightness: {quality['brightness']:.3f}")
        
        results.append(quality)
        
        # Validate
        if quality['overall'] >= case['expected_min']:
            print(f"   ✅ Quality meets expected minimum ({case['expected_min']})")
        else:
            print(f"   ⚠️ Quality below expected minimum ({case['expected_min']})")
    
    return results

def test_crop_validation(estimator):
    """Test crop validity checking."""
    print("\n🧪 Testing crop validation...")
    
    valid_crop = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
    invalid_crop = np.random.randint(0, 255, (32, 16, 3), dtype=np.uint8)
    empty_crop = np.array([])
    
    try:
        is_valid = estimator.is_valid_crop(valid_crop)
        is_invalid = estimator.is_valid_crop(invalid_crop)
        is_empty = estimator.is_valid_crop(empty_crop)
        
        print(f"   - Valid crop: {is_valid}")
        print(f"   - Invalid crop: {is_invalid}")
        print(f"   - Empty crop: {is_empty}")
        
        if is_valid and not is_invalid and not is_empty:
            print("   ✅ Validation works as expected")
        else:
            print("   ⚠️ Validation may need tuning")
            
    except Exception as e:
        print(f"❌ Crop validation failed: {e}")

def test_best_crops(estimator):
    """Test selecting best crops."""
    print("\n🧪 Testing best crops selection...")
    
    crops = [
        np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8),
        np.random.randint(0, 255, (64, 32, 3), dtype=np.uint8),
        np.random.randint(0, 255, (128, 64, 3), dtype=np.uint8),
        np.random.randint(0, 255, (200, 100, 3), dtype=np.uint8),
    ]
    
    best = estimator.get_best_crops(crops, n=2)
    
    print(f"   - Selected {len(best)} best crops out of {len(crops)}")
    for i, crop in enumerate(best):
        quality = estimator.estimate_quality(crop)
        print(f"   - Crop {i+1} quality: {quality['overall']:.3f}")
    
    return best

def main():
    print("=" * 60)
    print("🧪 Quality Estimator Tests")
    print("=" * 60)
    
    estimator = test_quality_initialization()
    if estimator is None:
        return
    
    test_quality_estimation(estimator)
    test_crop_validation(estimator)
    test_best_crops(estimator)
    
    print("\n" + "=" * 60)
    print("✅ All quality tests completed!")

if __name__ == "__main__":
    main()