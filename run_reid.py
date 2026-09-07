# run_reid.py
#!/usr/bin/env python3
"""
Multi-Camera Re-ID System - Phase 1 Entry Point
"""
import argparse
import cv2
import yaml
import sys
import os
from datetime import datetime
import logging

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from tracker.enhanced_tracker import EnhancedTracker
from utils.config import ConfigManager
from utils.visualization import draw_reid_info

def setup_logging():
    """Setup logging configuration."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('reid_pipeline.log'),
            logging.StreamHandler()
        ]
    )
    return logging.getLogger(__name__)

def process_video(video_path: str, camera_id: int, config_path: str = "config.yaml"):
    """Process a video with Re-ID capabilities."""
    logger = setup_logging()
    logger.info(f"Processing video: {video_path} (Camera {camera_id})")
    
    # Load configuration
    config = ConfigManager(config_path)
    
    # Initialize enhanced tracker
    tracker = EnhancedTracker(config.config)
    
    # Open video
    cap = cv2.VideoCapture(video_path)
    if not cap.isOpened():
        logger.error(f"Cannot open video: {video_path}")
        return
    
    frame_count = 0
    total_detections = 0
    
    while True:
        ret, frame = cap.read()
        if not ret:
            break
            
        frame_count += 1
        
        # Simulate detections (replace with your YOLO + ByteTrack)
        # For demonstration, we'll use a placeholder
        detections = []  # Your detection pipeline here
        
        # For each detection, add Re-ID
        for det in detections:
            # Assuming det has track_id and bbox
            track_id = det.get('track_id', f"T{frame_count:04d}")
            bbox = det.get('bbox', [0, 0, 100, 200])
            
            # Extract crop
            x1, y1, x2, y2 = map(int, bbox)
            crop = frame[y1:y2, x1:x2]
            
            if crop.size > 0:
                # Add to tracker with Re-ID
                enhanced_det = tracker.add_detection(
                    camera_id, track_id, bbox, crop, 
                    frame_count / cap.get(cv2.CAP_PROP_FPS)
                )
                
                # Visualize
                if enhanced_det and not enhanced_det.get('quality_skipped', True):
                    frame = draw_reid_info(frame, enhanced_det)
                    total_detections += 1
        
        # Display frame number
        cv2.putText(frame, f"Frame: {frame_count}", (10, 30),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        # Show statistics
        stats = tracker.get_statistics()
        cv2.putText(frame, f"Identities: {stats['total_identities']}", (10, 60),
                    cv2.FONT_HERSHEY_SIMPLEX, 0.7, (255, 255, 255), 2)
        
        cv2.imshow('Re-ID Tracking', frame)
        
        if cv2.waitKey(1) & 0xFF == ord('q'):
            break
    
    cap.release()
    cv2.destroyAllWindows()
    
    # Print final statistics
    logger.info("=== Pipeline Statistics ===")
    logger.info(f"Total frames: {frame_count}")
    logger.info(f"Total detections: {total_detections}")
    logger.info(f"Global identities: {stats['total_identities']}")
    logger.info(f"Total profiles: {stats['total_profiles']}")
    logger.info(f"Total matches: {stats['total_matches']}")

def main():
    parser = argparse.ArgumentParser(
        description='Multi-Camera Re-ID System - Phase 1'
    )
    parser.add_argument('--video', required=True, 
                       help='Path to video file')
    parser.add_argument('--camera', type=int, required=True,
                       help='Camera ID')
    parser.add_argument('--config', default='config.yaml',
                       help='Configuration file path')
    parser.add_argument('--visualize', action='store_true',
                       help='Enable visualization')
    
    args = parser.parse_args()
    
    # Check if video exists
    if not os.path.exists(args.video):
        print(f"❌ Video not found: {args.video}")
        sys.exit(1)
    
    # Process video
    process_video(args.video, args.camera, args.config)

if __name__ == "__main__":
    main()