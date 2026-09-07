# crowd/density_estimator.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from scipy.spatial import distance
from sklearn.cluster import DBSCAN

class DensityEstimator:
    """
    Estimate crowd density and distribution.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.min_samples = self.config.get('min_samples', 3)
        self.eps = self.config.get('cluster_eps', 0.5)
        self.camera_areas = self.config.get('camera_areas', {})
        
    def estimate_density(self, persons: List[Dict], 
                         camera_id: int) -> Dict:
        """
        Estimate crowd density for a set of persons.
        
        Returns:
            Dictionary with density metrics
        """
        if not persons:
            return {
                'density': 0,
                'cluster_count': 0,
                'avg_cluster_size': 0,
                'max_cluster_size': 0,
                'distribution': 'empty'
            }
        
        # Extract positions
        positions = []
        for person in persons:
            bbox = person.get('bbox', [0, 0, 100, 100])
            # Use center of bounding box
            x = (bbox[0] + bbox[2]) / 2
            y = (bbox[1] + bbox[3]) / 2
            positions.append([x, y])
        
        positions = np.array(positions)
        
        # Compute density
        area = self.camera_areas.get(camera_id, 100)
        density = len(persons) / area if area > 0 else 0
        
        # Cluster analysis
        clusters = self._find_clusters(positions)
        
        # Distribution analysis
        distribution = self._analyze_distribution(positions)
        
        return {
            'density': density,
            'cluster_count': len(clusters),
            'avg_cluster_size': np.mean([len(c) for c in clusters]) if clusters else 0,
            'max_cluster_size': max([len(c) for c in clusters]) if clusters else 0,
            'distribution': distribution,
            'positions': positions.tolist() if len(positions) < 100 else None
        }
    
    def _find_clusters(self, positions: np.ndarray) -> List[np.ndarray]:
        """Find clusters of people using DBSCAN."""
        if len(positions) < self.min_samples:
            return []
        
        # DBSCAN clustering
        clustering = DBSCAN(eps=self.eps, min_samples=self.min_samples).fit(positions)
        
        # Extract clusters
        clusters = []
        labels = clustering.labels_
        
        for label in set(labels):
            if label != -1:  # Ignore noise
                cluster_points = positions[labels == label]
                clusters.append(cluster_points)
        
        return clusters
    
    def _analyze_distribution(self, positions: np.ndarray) -> str:
        """Analyze distribution pattern."""
        if len(positions) < 2:
            return 'sparse'
        
        # Compute pairwise distances
        distances = distance.pdist(positions)
        
        if len(distances) == 0:
            return 'sparse'
        
        # Analyze distance distribution
        mean_dist = np.mean(distances)
        std_dist = np.std(distances)
        
        # Check for uniformity
        if std_dist < mean_dist * 0.2:
            return 'uniform'
        elif std_dist > mean_dist * 0.8:
            return 'clustered'
        else:
            return 'scattered'
    
    def get_density_map(self, persons: List[Dict],
                        camera_id: int,
                        grid_size: Tuple[int, int] = (10, 10)) -> np.ndarray:
        """
        Create a density heatmap for a camera view.
        """
        if not persons:
            return np.zeros(grid_size)
        
        # Extract positions (normalized 0-1)
        positions = []
        for person in persons:
            bbox = person.get('bbox', [0, 0, 1, 1])
            x = (bbox[0] + bbox[2]) / 2
            y = (bbox[1] + bbox[3]) / 2
            positions.append([x, y])
        
        positions = np.array(positions)
        
        # Create grid
        heatmap = np.zeros(grid_size)
        
        # Add Gaussian kernels for each person
        sigma = 0.1  # Kernel width
        for pos in positions:
            x, y = pos
            for i in range(grid_size[0]):
                for j in range(grid_size[1]):
                    xi = i / grid_size[0]
                    yj = j / grid_size[1]
                    heatmap[i, j] += np.exp(-((xi - x)**2 + (yj - y)**2) / (2 * sigma**2))
        
        # Normalize
        if np.max(heatmap) > 0:
            heatmap /= np.max(heatmap)
        
        return heatmap
    
    def get_hotspots(self, density_map: np.ndarray, 
                     threshold: float = 0.7) -> List[Tuple[int, int]]:
        """
        Find hotspots in a density map.
        """
        hotspots = []
        
        # Find cells above threshold
        for i in range(density_map.shape[0]):
            for j in range(density_map.shape[1]):
                if density_map[i, j] >= threshold:
                    # Check if it's a local maximum
                    is_local_max = True
                    for di in [-1, 0, 1]:
                        for dj in [-1, 0, 1]:
                            if di == 0 and dj == 0:
                                continue
                            ni, nj = i + di, j + dj
                            if 0 <= ni < density_map.shape[0] and 0 <= nj < density_map.shape[1]:
                                if density_map[ni, nj] > density_map[i, j]:
                                    is_local_max = False
                                    break
                        if not is_local_max:
                            break
                    
                    if is_local_max:
                        hotspots.append((i, j))
        
        return hotspots