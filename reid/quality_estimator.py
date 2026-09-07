# reid/quality_estimator.py
import cv2
import numpy as np
from typing import Tuple, Optional

class QualityEstimator:
    """Estimate quality of person crops for Re-ID."""
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.min_resolution = self.config.get('min_resolution', (64, 128))
        self.blur_threshold = self.config.get('blur_threshold', 1000)
        self.contrast_threshold = self.config.get('contrast_threshold', 30)
        
    def estimate_quality(self, crop: np.ndarray) -> dict:
        """
        Estimate quality of person crop.
        
        Returns:
            Dictionary with quality metrics
        """
        if crop is None or crop.size == 0:
            return {'overall': 0.0, 'resolution': 0.0, 'blur': 0.0, 
                    'contrast': 0.0, 'brightness': 0.0}
        
        h, w = crop.shape[:2]
        gray = cv2.cvtColor(crop, cv2.COLOR_BGR2GRAY)
        
        # Resolution score (higher is better)
        res_score = min(1.0, (h * w) / (self.min_resolution[0] * self.min_resolution[1]))
        
        # Blur detection using Laplacian variance
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(1.0, laplacian_var / self.blur_threshold)
        
        # Contrast
        contrast = np.std(gray)
        contrast_score = min(1.0, contrast / 128)
        
        # Brightness (0.5 is ideal)
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128
        
        # Combined quality score
        weights = [0.2, 0.4, 0.2, 0.2]  # resolution, blur, contrast, brightness
        overall = (res_score * weights[0] + 
                  blur_score * weights[1] + 
                  contrast_score * weights[2] + 
                  brightness_score * weights[3])
        
        return {
            'overall': float(overall),
            'resolution': float(res_score),
            'blur': float(blur_score),
            'contrast': float(contrast_score),
            'brightness': float(brightness_score),
            'resolution_actual': (h, w)
        }
    
    def is_valid_crop(self, crop: np.ndarray, min_quality: float = 0.3) -> bool:
        """Check if crop meets minimum quality threshold."""
        quality = self.estimate_quality(crop)
        return quality['overall'] >= min_quality
    
    def get_best_crops(self, crops: list, n: int = 3) -> list:
        """Get top N crops based on quality."""
        if not crops:
            return []
            
        quality_scores = []
        for crop in crops:
            q = self.estimate_quality(crop)
            quality_scores.append(q['overall'])
            
        indices = np.argsort(quality_scores)[-n:][::-1]
        return [crops[i] for i in indices]