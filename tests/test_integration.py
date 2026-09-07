# tests/test_integration.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
import time
from datetime import datetime

from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator
from reid.reid_gallery import ReIDGallery
from tracker.enhanced_tracker import EnhancedTracker

def generate_test_video():
    """Generate a synthetic test video with moving persons."""
    print("🧪 Generating test video...")
    
    width, height = 640, 480
    fps = 30
    duration = 5  # seconds
    total_frames = duration * fps
    
    # Create video writer
    fourcc = cv2.VideoWriter_fourcc(*'XVID')
    out = cv2.VideoWriter('tests/test_data/test_video.avi', fourcc, fps, (width, height))
    
    # Generate frames
    for i in range(total_frames):
        frame = np.ones((height, width, 3), dtype=np.uint8) * 128
        
        # Draw a moving person (rectangle)
        x = int(100 + 200 * (i / total_frames))
        y = int(200 + 100 * np.sin(2 * np.pi * i / total_frames))
        cv2.rectangle(frame, (x, y), (x+50, y+150), (0, 255, 0), -1)
        
        # Draw another person
        x2 = int(300 + 100 * np.sin(2 * np.pi * i / total_frames * 0.5))
        y2 = int(300 + 50 * np.cos(2 * np.pi * i / total_frames * 0.3))
        cv2.rectangle(frame, (x2, y2), (x2+40, y2+120), (0, 0, 255), -1)
        
        out.write(frame)
    
    out.release()
    print(f"✅ Test video generated: tests/test_data/test_video.avi")
    return "tests/test_data/test_video.avi"

def test_enhanced_tracker(video_path):
    """Test EnhancedTracker on synthetic video."""
    print("\n🧪 Testing EnhancedTracker...")
    
    config = {
        'reid': {
            'model_path': None,
            'device': 'cpu',
            'input_size': [128, 64],
            'matching': {
                'threshold': 0.3
            }
        },
        'database': {
            'path': 'tests/test_data/test_reid.db'
        }
    }
    
    # Initialize tracker
    tracker = EnhancedTracker(config)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        print(f"❌ Cannot open video: {video_path}")
        return
    
    frame_count = 0
    detections_count = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Simulate detections using color-based blob detection
        # In real scenario, this would be YOLO + ByteTrack
        gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
        _, thresh = cv2.threshold(gray, 100, 255, cv2.THRESH_BINARY)
        contours, _ = cv2.findContours(thresh, cv2.RETR_EXTERNAL, cv2.CHAIN_APPROX_SIMPLE)
        
        for contour in contours:
            x, y, w, h = cv2.boundingRect(contour)
            if w > 20 and h > 50:  # Minimum person size
                track_id = f"T{frame_count:04d}_{len(contours)}"
                bbox = [x, y, x+w, y+h]
                crop = frame[y:y+h, x:x+w]
                
                if crop.size > 0:
                    enhanced_det = tracker.add_detection(
                        0, track_id, bbox, crop, frame_count / 30.0
                    )
                    
                    if enhanced_det and not enhanced_det.get('quality_skipped', True):
                        detections_count += 1
        
        # Show progress
        if frame_count % 30 == 0:
            print(f"   - Processed frame {frame_count}/{cap.get(cv2.CAP_PROP_FRAME_COUNT)}")
    
    cap.release()
    
    # Get statistics
    stats = tracker.get_statistics()
    print(f"\n   ✅ Tracker statistics:")
    print(f"   - Total frames: {frame_count}")
    print(f"   - Detections processed: {detections_count}")
    print(f"   - Global identities: {stats['total_identities']}")
    print(f"   - Total profiles: {stats['total_profiles']}")
    
    return stats

def run_manual_cross_camera_test():
    """Manual test of cross-camera matching."""
    print("\n🧪 Manual cross-camera matching test...")
    
    # Create two galleries
    gallery1 = ReIDGallery("tests/test_data/gallery1.db")
    gallery2 = ReIDGallery("tests/test_data/gallery2.db")
    
    # Generate same person embedding
    person_emb = np.random.randn(512)
    person_emb = person_emb / np.linalg.norm(person_emb)
    
    # Add to camera 1
    id1 = gallery1.add_observation(0, "T001", person_emb, 0.8, datetime.now())
    print(f"   - Added person to Camera 1: {id1}")
    
    # Add same person to camera 2 (should match)
    id2 = gallery2.add_observation(1, "T002", person_emb, 0.75, datetime.now())
    print(f"   - Added same person to Camera 2: {id2}")
    
    # Check if they matched (cross-camera)
    if id1 == id2:
        print("   ✅ Cross-camera match successful!")
    else:
        print("   ❌ Cross-camera match failed")
        print(f"      ID1: {id1}, ID2: {id2}")
    
    # Different person
    other_emb = np.random.randn(512)
    other_emb = other_emb / np.linalg.norm(other_emb)
    id3 = gallery2.add_observation(1, "T003", other_emb, 0.7, datetime.now())
    print(f"   - Added different person to Camera 2: {id3}")
    
    if id2 != id3:
        print("   ✅ Different persons correctly separated")
    else:
        print("   ❌ Different persons incorrectly matched")
    
    return id1, id2, id3

def main():
    print("=" * 60)
    print("🧪 Integration Tests - Phase 1")
    print("=" * 60)
    
    # Test 1: Generate test video
    video_path = generate_test_video()
    
    # Test 2: Run enhanced tracker
    test_enhanced_tracker(video_path)
    
    # Test 3: Manual cross-camera test
    run_manual_cross_camera_test()
    
    print("\n" + "=" * 60)
    print("✅ All integration tests completed!")

if __name__ == "__main__":
    main()