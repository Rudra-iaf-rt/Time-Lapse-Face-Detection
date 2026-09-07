# reid/multimodal_fusion.py
import numpy as np
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json
from topology.camera_graph import CameraGraph
from topology.spatial_consistency import SpatialConsistencyChecker
from topology.temporal_consistency import TemporalConsistencyChecker

class MultimodalFusionEngine:
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        
        # Initialize topology components
        self.camera_graph = CameraGraph(
            self.config.get('database', {}).get('path', 'database/identities.db')
        )
        self.spatial_checker = SpatialConsistencyChecker(
            self.camera_graph,
            max_time_gap=self.config.get('topology', {}).get('spatial', {}).get('max_time_gap', 300.0),
            min_probability=self.config.get('topology', {}).get('spatial', {}).get('min_probability', 0.1)
        )
        self.temporal_checker = TemporalConsistencyChecker(
            max_time_gap=self.config.get('topology', {}).get('temporal', {}).get('max_time_gap', 300.0),
            min_overlap=self.config.get('topology', {}).get('temporal', {}).get('min_overlap', 0.3)
        )
        
        # Fusion weights (updated)
        self.weights = {
            'face': self.config.get('fusion', {}).get('weights', {}).get('face', 0.35),
            'reid': self.config.get('fusion', {}).get('weights', {}).get('reid', 0.30),
            'appearance': self.config.get('fusion', {}).get('weights', {}).get('appearance', 0.10),
            'temporal': self.config.get('fusion', {}).get('weights', {}).get('temporal', 0.10),
            'spatial': self.config.get('fusion', {}).get('weights', {}).get('spatial', 0.15)
        }
        
        # Thresholds
        self.fusion_threshold = self.config.get('fusion', {}).get('thresholds', {}).get('fusion', 0.65)
        self.face_threshold = self.config.get('fusion', {}).get('thresholds', {}).get('face', 0.6)
        self.reid_threshold = self.config.get('fusion', {}).get('thresholds', {}).get('reid', 0.55)
        
        # Quality thresholds
        self.min_face_quality = self.config.get('fusion', {}).get('quality', {}).get('min_face', 0.3)
        self.min_reid_quality = self.config.get('fusion', {}).get('quality', {}).get('min_reid', 0.3)
    
    def fuse_identities(self,
                        face_similarity: float,
                        reid_similarity: float,
                        appearance_similarity: float,
                        camera1: int = -1,
                        camera2: int = -1,
                        time1: Optional[datetime] = None,
                        time2: Optional[datetime] = None,
                        face_quality: float = 0.5,
                        reid_quality: float = 0.5) -> Dict:
        """Updated fusion with topology."""
        
        # Compute temporal and spatial scores
        temporal_score = 0.5
        if time1 and time2:
            temporal_score = self.temporal_checker.compute_temporal_score(
                {'start_time': time1, 'end_time': time1},
                {'start_time': time2, 'end_time': time2}
            )
        
        spatial_score = 0.5
        if camera1 >= 0 and camera2 >= 0 and time1 and time2:
            spatial_result = self.spatial_checker.check_consistency(
                camera1, camera2, time1, time2
            )
            spatial_score = spatial_result['score']
        
        # Apply quality weighting
        face_weighted = face_similarity * (0.7 + 0.3 * face_quality)
        reid_weighted = reid_similarity * (0.7 + 0.3 * reid_quality)
        
        # Check for low quality - reduce weight
        if face_quality < self.min_face_quality:
            face_weight = self.weights['face'] * 0.3
        else:
            face_weight = self.weights['face']
        
        if reid_quality < self.min_reid_quality:
            reid_weight = self.weights['reid'] * 0.3
        else:
            reid_weight = self.weights['reid']
        
        # Boost spatial weight if cameras are known
        if camera1 >= 0 and camera2 >= 0:
            spatial_weight = self.weights['spatial'] * 1.2
        else:
            spatial_weight = self.weights['spatial']
        
        # Normalize weights
        total_weight = (face_weight + reid_weight + 
                       self.weights['appearance'] + 
                       self.weights['temporal'] + 
                       spatial_weight)
        
        # Compute weighted fusion score
        fusion_score = (
            face_weighted * face_weight +
            reid_weighted * reid_weight +
            appearance_similarity * self.weights['appearance'] +
            temporal_score * self.weights['temporal'] +
            spatial_score * spatial_weight
        ) / total_weight
        
        # Determine if it's a match
        is_match = fusion_score >= self.fusion_threshold
        
        # Face matching decision
        face_match = face_similarity >= self.face_threshold
        
        # Re-ID matching decision
        reid_match = reid_similarity >= self.reid_threshold
        
        # Topology-based decision
        topology_ok = spatial_score > 0.3
        
        # Consensus decision
        if face_match and reid_match and topology_ok:
            confidence = min(1.0, fusion_score * 1.2)
            decision = 'MATCH'
        elif face_match and topology_ok:
            confidence = min(1.0, fusion_score * 1.1)
            decision = 'FACE_MATCH'
        elif reid_match and topology_ok:
            confidence = min(1.0, fusion_score * 1.1)
            decision = 'REID_MATCH'
        elif fusion_score >= 0.5:
            confidence = fusion_score * 0.9
            decision = 'LOW_CONFIDENCE'
        else:
            confidence = fusion_score * 0.5
            decision = 'NO_MATCH'
        
        return {
            'fusion_score': float(fusion_score),
            'is_match': is_match,
            'decision': decision,
            'confidence': float(confidence),
            'face_similarity': float(face_similarity),
            'reid_similarity': float(reid_similarity),
            'appearance_similarity': float(appearance_similarity),
            'temporal_score': float(temporal_score),
            'spatial_score': float(spatial_score),
            'face_quality': float(face_quality),
            'reid_quality': float(reid_quality),
            'topology_ok': topology_ok,
            'weights_used': {
                'face': float(face_weight / total_weight),
                'reid': float(reid_weight / total_weight),
                'appearance': float(self.weights['appearance'] / total_weight),
                'temporal': float(self.weights['temporal'] / total_weight),
                'spatial': float(spatial_weight / total_weight)
            }
        }
    
    def compute_temporal_score(self, 
                              time1: datetime, 
                              time2: datetime,
                              max_time_diff: float = 300.0) -> float:
        """Compute temporal consistency score."""
        time_diff = abs((time2 - time1).total_seconds())
        
        if time_diff > max_time_diff:
            return 0.0
        
        # Exponential decay
        score = np.exp(-time_diff / (max_time_diff / 3))
        return float(score)
    
    def compute_spatial_score(self,
                             camera1: int,
                             camera2: int,
                             camera_topology: Dict) -> float:
        """Compute spatial consistency score using camera topology."""
        if camera1 == camera2:
            return 0.8
        
        # Get transition probability from topology
        transition_prob = camera_topology.get(camera1, {}).get(camera2, 0.0)
        
        if transition_prob > 0:
            return float(transition_prob)
        else:
            return 0.2
    
    def compute_appearance_similarity(self,
                                     person1_emb: np.ndarray,
                                     person2_emb: np.ndarray,
                                     method: str = 'cosine') -> float:
        """Compute appearance similarity."""
        if method == 'cosine':
            return float(np.dot(person1_emb, person2_emb))
        elif method == 'euclidean':
            distance = np.linalg.norm(person1_emb - person2_emb)
            return float(np.exp(-distance / 10.0))
        else:
            return 0.0

class IdentityFusionManager:
    """
    Manage identity fusion across the system.
    """
    
    def __init__(self, config: dict = None):
        self.fusion_engine = MultimodalFusionEngine(config)
        self.gallery = {}
        self.fusion_history = []
        
    def add_observation(self, 
                       global_id: str,
                       face_embedding: Optional[np.ndarray] = None,
                       reid_embedding: Optional[np.ndarray] = None,
                       appearance_embedding: Optional[np.ndarray] = None,
                       face_quality: float = 0.0,
                       reid_quality: float = 0.0,
                       camera_id: int = 0,
                       timestamp: datetime = None):
        """
        Add an observation for identity fusion.
        """
        if global_id not in self.gallery:
            self.gallery[global_id] = {
                'face_embedding': [],
                'reid_embedding': [],
                'appearance_embedding': [],
                'face_quality': [],
                'reid_quality': [],
                'cameras': [],
                'timestamps': []
            }
        
        # Add to gallery
        if face_embedding is not None:
            self.gallery[global_id]['face_embedding'].append(face_embedding)
            self.gallery[global_id]['face_quality'].append(face_quality)
        
        if reid_embedding is not None:
            self.gallery[global_id]['reid_embedding'].append(reid_embedding)
            self.gallery[global_id]['reid_quality'].append(reid_quality)
        
        if appearance_embedding is not None:
            self.gallery[global_id]['appearance_embedding'].append(appearance_embedding)
        
        self.gallery[global_id]['cameras'].append(camera_id)
        self.gallery[global_id]['timestamps'].append(timestamp or datetime.now())
    
    def find_matches(self, 
                     query: Dict,
                     threshold: float = 0.6) -> List[Dict]:
        """
        Find matching identities in the gallery.
        """
        matches = []
        
        for global_id, gallery_data in self.gallery.items():
            # Get best embeddings
            face_emb = self._get_best_embedding(gallery_data['face_embedding'],
                                               gallery_data.get('face_quality', [1.0]))
            reid_emb = self._get_best_embedding(gallery_data['reid_embedding'],
                                               gallery_data.get('reid_quality', [1.0]))
            
            # Compute similarities
            face_sim = 0.0
            if face_emb is not None and query.get('face_embedding') is not None:
                face_sim = np.dot(face_emb, query['face_embedding'])
            
            reid_sim = 0.0
            if reid_emb is not None and query.get('reid_embedding') is not None:
                reid_sim = np.dot(reid_emb, query['reid_embedding'])
            
            # Compute fusion score
            result = self.fusion_engine.fuse_identities(
                face_similarity=face_sim,
                reid_similarity=reid_sim,
                appearance_similarity=0.5,
                face_quality=query.get('face_quality', 0.5),
                reid_quality=query.get('reid_quality', 0.5)
            )
            
            if result['fusion_score'] > threshold:
                matches.append({
                    'global_id': global_id,
                    'fusion_score': result['fusion_score'],
                    'face_similarity': face_sim,
                    'reid_similarity': reid_sim,
                    'decision': result['decision']
                })
        
        # Sort by fusion score
        matches.sort(key=lambda x: x['fusion_score'], reverse=True)
        
        return matches
    
    def _get_best_embedding(self, embeddings: list, 
                           qualities: list) -> Optional[np.ndarray]:
        """Get the best embedding based on quality."""
        if not embeddings:
            return None
        
        if not qualities or len(qualities) != len(embeddings):
            # Return latest or average
            if len(embeddings) == 1:
                return embeddings[0]
            else:
                return np.mean(embeddings, axis=0)
        
        # Get embedding with highest quality
        best_idx = np.argmax(qualities)
        return embeddings[best_idx]
    
    def get_identity_quality(self, global_id: str) -> float:
        """Get overall quality score for an identity."""
        if global_id not in self.gallery:
            return 0.0
        
        data = self.gallery[global_id]
        
        # Average face and reid qualities
        face_quality = np.mean(data.get('face_quality', [0.0])) if data.get('face_quality') else 0.0
        reid_quality = np.mean(data.get('reid_quality', [0.0])) if data.get('reid_quality') else 0.0
        
        # Combine
        return float(0.5 * face_quality + 0.5 * reid_quality)