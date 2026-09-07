"""
pipeline.py
-----------
Main entry point for the Multi-Camera Tracking & Re-ID system.

Usage — video files
-------------------
  python pipeline.py --videos cam0.mp4 cam1.mp4 --output results/

Usage — live RTSP streams
-------------------------
  python pipeline.py --live \
    --sources rtsp://192.168.1.10/stream1 rtsp://192.168.1.11/stream2 \
    --output results/

Usage — mixed (file + webcam)
------------------------------
  python pipeline.py --live --sources cam0.mp4 0 --output results/

Then open the dashboard in a separate terminal:
  streamlit run dashboard/app.py

Key flags
---------
  --lost-threshold   seconds absent before person → LOST   [120]
  --sim-threshold    cosine similarity for identity match  [0.60]
  --reentry-timeout  alias for lost-threshold (same value)
"""

import argparse
import time
from pathlib import Path

from tracker.global_tracker import GlobalTracker
# pipeline.py - Updated with Face Integration
import cv2
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime

from face.face_detector import FaceDetector
from face.face_aligner import FaceAligner
from face.face_embedder import ArcFaceEmbedder
from face.face_quality import FaceQualityEstimator
from face.face_gallery import FaceGallery
from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator
from reid.reid_gallery import ReIDGallery
from reid.multimodal_fusion import MultimodalFusionEngine, IdentityFusionManager

class MultiCameraPipeline:
    """Complete multi-camera pipeline with face + Re-ID."""
    
    def __init__(self, config: dict):
        self.config = config
        
        # Initialize Re-ID components
        self.reid_extractor = OSNetReIDExtractor(
            model_path=config.get('reid', {}).get('model_path'),
            device=config.get('reid', {}).get('device', 'cuda')
        )
        self.reid_quality = QualityEstimator()
        self.reid_gallery = ReIDGallery(config.get('database', {}).get('path'))
        
        # Initialize Face components
        face_config = config.get('face', {})
        self.face_detector = FaceDetector(
            method=face_config.get('detector', 'mtcnn'),
            device=face_config.get('device', 'cuda'),
            min_face_size=face_config.get('min_face_size', 20),
            confidence_threshold=face_config.get('confidence_threshold', 0.9)
        )
        self.face_aligner = FaceAligner(
            output_size=tuple(face_config.get('input_size', [112, 112]))
        )
        self.face_embedder = ArcFaceEmbedder(
            model_path=face_config.get('model_path'),
            device=face_config.get('device', 'cuda')
        )
        self.face_quality = FaceQualityEstimator()
        self.face_gallery = FaceGallery(config.get('database', {}).get('path'))
        
        # Initialize fusion engine
        self.fusion_engine = MultimodalFusionEngine(config.get('fusion', {}))
        self.identity_manager = IdentityFusionManager(config.get('fusion', {}))
        
        # Track cache
        self.track_cache = {}
    
    def process_frame(self, camera_id: int, frame: np.ndarray,
                     detections: List[Dict]) -> List[Dict]:
        """
        Process a frame with both Re-ID and face recognition.
        """
        enhanced_detections = []
        
        for det in detections:
            track_id = det['track_id']
            bbox = det['bbox']
            x1, y1, x2, y2 = map(int, bbox)
            
            # Extract person crop
            person_crop = frame[y1:y2, x1:x2]
            if person_crop.size == 0:
                continue
            
            # 1. Re-ID extraction
            reid_embedding = self.reid_extractor.extract_embedding(person_crop)
            reid_quality = self.reid_quality.estimate_quality(person_crop)
            reid_quality_score = reid_quality['overall']
            
            # 2. Face detection within person crop
            faces = self.face_detector.get_faces_with_person(person_crop, bbox)
            
            face_embedding = None
            face_quality_score = 0.0
            face_bbox = None
            
            if faces:
                # Get best quality face
                best_face = max(faces, key=lambda x: x.get('confidence', 0))
                
                # Align face
                face_crop = person_crop[
                    best_face['bbox'][1]:best_face['bbox'][3],
                    best_face['bbox'][0]:best_face['bbox'][2]
                ]
                
                if face_crop.size > 0:
                    # Align and extract embedding
                    aligned_face = self.face_aligner.align_face(
                        face_crop, best_face.get('landmarks')
                    )
                    
                    if aligned_face is not None:
                        face_embedding = self.face_embedder.extract_embedding(aligned_face)
                        face_quality = self.face_quality.estimate_quality(
                            aligned_face, best_face.get('landmarks')
                        )
                        face_quality_score = face_quality['overall']
                        face_bbox = best_face['bbox_original']
            
            # 3. Determine identity using fusion
            timestamp = datetime.now()
            
            # Check if we have an existing global ID for this track
            existing_global_id = self.reid_gallery.get_global_id(camera_id, track_id)
            
            if existing_global_id:
                # Add to identity manager
                self.identity_manager.add_observation(
                    global_id=existing_global_id,
                    face_embedding=face_embedding,
                    reid_embedding=reid_embedding,
                    face_quality=face_quality_score,
                    reid_quality=reid_quality_score,
                    camera_id=camera_id,
                    timestamp=timestamp
                )
                
                # Add face to face gallery
                if face_embedding is not None and face_quality_score > 0.3:
                    self.face_gallery.add_face(
                        global_id=existing_global_id,
                        face_embedding=face_embedding,
                        quality=face_quality_score,
                        bbox=face_bbox if face_bbox else bbox,
                        camera_id=camera_id,
                        track_id=track_id,
                        timestamp=timestamp
                    )
                
                global_id = existing_global_id
                
            else:
                # Try to match with existing identities
                query = {
                    'face_embedding': face_embedding,
                    'reid_embedding': reid_embedding,
                    'face_quality': face_quality_score,
                    'reid_quality': reid_quality_score
                }
                
                matches = self.identity_manager.find_matches(query)
                
                if matches and matches[0]['fusion_score'] > 0.65:
                    # Match found
                    global_id = matches[0]['global_id']
                    
                    # Update galleries
                    self.reid_gallery.add_observation(
                        camera_id, track_id, reid_embedding,
                        reid_quality_score, timestamp
                    )
                    
                    if face_embedding is not None:
                        self.face_gallery.add_face(
                            global_id=global_id,
                            face_embedding=face_embedding,
                            quality=face_quality_score,
                            bbox=face_bbox if face_bbox else bbox,
                            camera_id=camera_id,
                            track_id=track_id,
                            timestamp=timestamp
                        )
                    
                    self.identity_manager.add_observation(
                        global_id=global_id,
                        face_embedding=face_embedding,
                        reid_embedding=reid_embedding,
                        face_quality=face_quality_score,
                        reid_quality=reid_quality_score,
                        camera_id=camera_id,
                        timestamp=timestamp
                    )
                    
                else:
                    # Create new identity
                    global_id = self.reid_gallery.add_observation(
                        camera_id, track_id, reid_embedding,
                        reid_quality_score, timestamp
                    )
                    
                    if face_embedding is not None:
                        self.face_gallery.add_face(
                            global_id=global_id,
                            face_embedding=face_embedding,
                            quality=face_quality_score,
                            bbox=face_bbox if face_bbox else bbox,
                            camera_id=camera_id,
                            track_id=track_id,
                            timestamp=timestamp
                        )
                    
                    self.identity_manager.add_observation(
                        global_id=global_id,
                        face_embedding=face_embedding,
                        reid_embedding=reid_embedding,
                        face_quality=face_quality_score,
                        reid_quality=reid_quality_score,
                        camera_id=camera_id,
                        timestamp=timestamp
                    )
            
            # Create enhanced detection
            enhanced_det = {
                'track_id': track_id,
                'bbox': bbox,
                'global_id': global_id,
                'reid_embedding': reid_embedding,
                'reid_quality': reid_quality_score,
                'face_embedding': face_embedding,
                'face_quality': face_quality_score,
                'face_detected': face_embedding is not None,
                'fusion_confidence': self._get_fusion_confidence(global_id)
            }
            
            enhanced_detections.append(enhanced_det)
        
        return enhanced_detections
    
    def _get_fusion_confidence(self, global_id: str) -> float:
        """Get fusion confidence for a global ID."""
        quality = self.identity_manager.get_identity_quality(global_id)
        return min(1.0, quality * 1.2)
    
    def get_statistics(self) -> Dict:
        """Get system statistics."""
        return {
            'reid': self.reid_gallery.get_statistics(),
            'face': self.face_gallery.get_gallery_statistics(),
            'total_identities': len(self.identity_manager.gallery)
        }

def main():
    p = argparse.ArgumentParser(
        description="Multi-Camera Person Tracking & Re-Identification"
    )

    # Sources
    source_group = p.add_mutually_exclusive_group(required=True)
    source_group.add_argument(
        "--videos", nargs="+",
        help="Video file paths (offline processing)"
    )
    source_group.add_argument(
        "--live", action="store_true",
        help="Live mode — use --sources for RTSP URLs or webcam indices"
    )
    p.add_argument(
        "--sources", nargs="+",
        help="For --live mode: RTSP URLs or webcam indices (e.g. 0 1)"
    )

    # Output
    p.add_argument("--output",          default="results",
                   help="Output directory  [results]")
    p.add_argument("--db",              default="database/identities.db",
                   help="SQLite database path")

    # Model
    p.add_argument("--yolo-model",      default="yolov8n.pt",
                   help="YOLOv8 variant: n/s/m/l/x.pt  [yolov8n.pt]")
    p.add_argument("--reid-weights",    default=None,
                   help="Optional fine-tuned ReID .pth")

    # Thresholds
    p.add_argument("--conf",            type=float, default=0.35,
                   help="Detection confidence  [0.35]")
    p.add_argument("--sim-threshold",   type=float, default=0.60,
                   help="Identity match cosine threshold  [0.60]")
    p.add_argument("--lost-threshold",  type=float, default=120.0,
                   help="Seconds absent → LOST status  [120]")

    # System
    p.add_argument("--device",          default="auto",
                   choices=["auto", "cuda", "cpu"])
    p.add_argument("--no-video",        action="store_true",
                   help="Don't save output videos (faster)")

    args = p.parse_args()

    # Resolve sources
    if args.videos:
        sources = args.videos
        live = False
    else:
        if not args.sources:
            p.error("--live requires --sources")
        # Convert numeric strings to ints (webcam indices)
        sources = [int(s) if s.isdigit() else s for s in args.sources]
        live = True

    _banner(sources, args.output, args.device,
            args.sim_threshold, args.lost_threshold)

    tracker = GlobalTracker(
        sources=sources,
        output_dir=args.output,
        db_path=args.db,
        reid_weights=args.reid_weights,
        yolo_model=args.yolo_model,
        conf=args.conf,
        sim_threshold=args.sim_threshold,
        lost_threshold=args.lost_threshold,
        device=args.device,
    )

    if live:
        print("\n🎥  Live mode — press Ctrl+C to stop\n")
        tracker.run_live()
    else:
        print("\n📹  Processing video files ...\n")
        t0 = time.time()
        all_tracks = tracker.run_files()
        elapsed = time.time() - t0

        # Print summary
        stats = tracker.store.stats()
        print("\n" + "═" * 55)
        print("  PIPELINE COMPLETE")
        print("═" * 55)
        for cam_id, cam_data in all_tracks.items():
            n_frames  = len(cam_data)
            n_gids    = len({d["global_id"]
                             for fd in cam_data.values() for d in fd})
            print(f"  Camera {cam_id}: {n_frames} frames | {n_gids} unique persons")
        print(f"\n  DB stats:")
        print(f"    Active   : {stats['active']}")
        print(f"    Lost     : {stats['lost']}")
        print(f"    Resolved : {stats['resolved']}")
        print(f"    Sightings: {stats['sightings']}")
        print(f"\n  Time: {elapsed:.1f}s")
        print("═" * 55)
        print(f"\n  Results  → {args.output}/")
        print(f"  Database → {args.db}")
        print(f"\n  Open dashboard:  streamlit run dashboard/app.py\n")


def _banner(sources, out, device, sim_thr, lost_thr):
    print("\n" + "═" * 55)
    print("  Multi-Camera Tracking & Re-ID")
    print("═" * 55)
    print(f"  Sources          : {len(sources)} camera(s)")
    for i, s in enumerate(sources):
        print(f"    [{i}] {s}")
    print(f"  Output           : {out}")
    print(f"  Device           : {device}")
    print(f"  Sim threshold    : {sim_thr}  (identity match)")
    print(f"  Lost threshold   : {lost_thr}s  (absent → LOST)")
    print("═" * 55)


if __name__ == "__main__":
    main()
