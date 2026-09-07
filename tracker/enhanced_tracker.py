# tracker/enhanced_tracker.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import deque
import cv2

from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator
from reid.reid_gallery import ReIDGallery

class EnhancedTracker:
    """
    Enhanced tracker that integrates Re-ID capabilities.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.reid_config = config.get('reid', {})
        
        # Initialize Re-ID components
        self.reid_extractor = OSNetReIDExtractor(
            model_path=self.reid_config.get('model_path'),
            device=self.reid_config.get('device', 'cuda'),
            input_size=tuple(self.reid_config.get('input_size', [256, 128]))
        )
        
        self.quality_estimator = QualityEstimator(
            self.reid_config.get('quality', {})
        )
        
        self.gallery = ReIDGallery(
            config.get('database', {}).get('path', 'database/identities.db')
        )
        
        # Track cache for speed
        self.embedding_cache = {}
        self.track_history = {}  # track_id -> list of observations
        
        self.matching_threshold = self.reid_config.get('matching', {}).get('threshold', 0.55)
    
    def add_detection(self, camera_id: int, track_id: str,
                     bbox: List[float], crop: np.ndarray,
                     timestamp: float) -> Dict:
        """
        Add a detection with Re-ID embedding.
        
        Returns:
            Enhanced detection with Re-ID information
        """
        # Extract Re-ID embedding
        embedding = self.reid_extractor.extract_embedding(crop)
        
        # Estimate quality
        quality = self.quality_estimator.estimate_quality(crop)
        
        # Skip low quality
        if quality['overall'] < 0.3:
            return {
                'track_id': track_id,
                'bbox': bbox,
                'reid_embedding': None,
                'reid_quality': quality,
                'global_id': None,
                'quality_skipped': True
            }
        
        # Add to gallery
        import datetime
        global_id = self.gallery.add_observation(
            camera_id, track_id, embedding, quality['overall'],
            datetime.datetime.fromtimestamp(timestamp)
        )
        
        # Cache embedding
        self.embedding_cache[track_id] = embedding
        
        # Update history
        if track_id not in self.track_history:
            self.track_history[track_id] = []
        self.track_history[track_id].append({
            'timestamp': timestamp,
            'embedding': embedding,
            'quality': quality
        })
        
        return {
            'track_id': track_id,
            'bbox': bbox,
            'reid_embedding': embedding,
            'reid_quality': quality,
            'global_id': global_id,
            'quality_skipped': False
        }
    
    def get_global_id(self, camera_id: int, track_id: str) -> Optional[str]:
        """Get global ID for a track."""
        return self.gallery.get_global_id(camera_id, track_id)
    
    def get_statistics(self) -> dict:
        """Get Re-ID system statistics."""
        stats = self.gallery.get_statistics()
        stats.update({
            'cached_tracks': len(self.embedding_cache),
            'historical_tracks': len(self.track_history)
        })
        return stats
    
    def clear_cache(self):
        """Clear embedding cache."""
        self.embedding_cache = {}