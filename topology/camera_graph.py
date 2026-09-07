# topology/camera_graph.py
import networkx as nx
import numpy as np
from typing import Dict, List, Tuple, Optional, Any
from dataclasses import dataclass
from datetime import datetime
import json

@dataclass
class CameraTransition:
    """Represents a transition between cameras."""
    from_camera: int
    to_camera: int
    transition_probability: float
    avg_travel_time: float
    min_travel_time: float
    max_travel_time: float
    std_travel_time: float
    observation_count: int
    last_observed: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        """Convert to dictionary for storage."""
        return {
            'from_camera': self.from_camera,
            'to_camera': self.to_camera,
            'transition_probability': self.transition_probability,
            'avg_travel_time': self.avg_travel_time,
            'min_travel_time': self.min_travel_time,
            'max_travel_time': self.max_travel_time,
            'std_travel_time': self.std_travel_time,
            'observation_count': self.observation_count,
            'last_observed': self.last_observed.isoformat() if self.last_observed else None
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'CameraTransition':
        """Create from dictionary."""
        return cls(
            from_camera=data['from_camera'],
            to_camera=data['to_camera'],
            transition_probability=data['transition_probability'],
            avg_travel_time=data['avg_travel_time'],
            min_travel_time=data['min_travel_time'],
            max_travel_time=data['max_travel_time'],
            std_travel_time=data['std_travel_time'],
            observation_count=data['observation_count'],
            last_observed=datetime.fromisoformat(data['last_observed']) if data['last_observed'] else None
        )

class CameraGraph:
    """
    Camera topology graph with transition probabilities and travel times.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self.graph = nx.DiGraph()
        self.transitions: Dict[Tuple[int, int], CameraTransition] = {}
        self._load_from_database()
    
    def add_camera(self, camera_id: int, 
                   position: Optional[Tuple[float, float]] = None,
                   metadata: Optional[Dict] = None):
        """Add a camera node to the graph."""
        self.graph.add_node(camera_id, 
                           position=position,
                           metadata=metadata or {})
    
    def add_transition(self, from_camera: int, to_camera: int,
                       transition: CameraTransition):
        """Add or update a camera transition."""
        # Validate cameras exist
        if from_camera not in self.graph:
            self.add_camera(from_camera)
        if to_camera not in self.graph:
            self.add_camera(to_camera)
        
        # Store transition
        key = (from_camera, to_camera)
        self.transitions[key] = transition
        
        # Update graph edge
        self.graph.add_edge(from_camera, to_camera,
                           weight=transition.transition_probability,
                           travel_time=transition.avg_travel_time)
    
    def get_transition(self, from_camera: int, 
                      to_camera: int) -> Optional[CameraTransition]:
        """Get transition between two cameras."""
        key = (from_camera, to_camera)
        return self.transitions.get(key)
    
    def get_transition_probability(self, from_camera: int,
                                   to_camera: int) -> float:
        """Get transition probability between two cameras."""
        transition = self.get_transition(from_camera, to_camera)
        return transition.transition_probability if transition else 0.0
    
    def get_avg_travel_time(self, from_camera: int, 
                           to_camera: int) -> Optional[float]:
        """Get average travel time between cameras."""
        transition = self.get_transition(from_camera, to_camera)
        return transition.avg_travel_time if transition else None
    
    def get_possible_destinations(self, camera_id: int) -> List[int]:
        """Get all possible destinations from a camera."""
        destinations = []
        for (from_cam, to_cam) in self.transitions.keys():
            if from_cam == camera_id:
                destinations.append(to_cam)
        return destinations
    
    def get_possible_sources(self, camera_id: int) -> List[int]:
        """Get all possible sources to a camera."""
        sources = []
        for (from_cam, to_cam) in self.transitions.keys():
            if to_cam == camera_id:
                sources.append(from_cam)
        return sources
    
    def get_path(self, from_camera: int, to_camera: int) -> List[int]:
        """
        Get the most likely path between two cameras.
        
        Returns:
            List of camera IDs representing the path
        """
        try:
            # Use shortest path based on transition probabilities
            path = nx.shortest_path(self.graph, from_camera, to_camera, 
                                   weight='weight')
            return path
        except nx.NetworkXNoPath:
            return []
    
    def get_travel_time_range(self, from_camera: int, 
                             to_camera: int) -> Tuple[float, float]:
        """Get the expected travel time range between cameras."""
        transition = self.get_transition(from_camera, to_camera)
        if transition:
            return (transition.min_travel_time, transition.max_travel_time)
        return (0, float('inf'))
    
    def is_transition_possible(self, from_camera: int,
                              to_camera: int,
                              time_diff: float) -> bool:
        """
        Check if a transition is possible within a time difference.
        
        Args:
            from_camera: Source camera
            to_camera: Destination camera
            time_diff: Time difference in seconds
            
        Returns:
            True if transition is possible
        """
        transition = self.get_transition(from_camera, to_camera)
        if not transition:
            return False
        
        # Check if time diff is within expected range
        if transition.min_travel_time <= time_diff <= transition.max_travel_time:
            return True
        
        # Allow some tolerance
        tolerance = 0.2  # 20% tolerance
        min_allowed = transition.min_travel_time * (1 - tolerance)
        max_allowed = transition.max_travel_time * (1 + tolerance)
        
        return min_allowed <= time_diff <= max_allowed
    
    def compute_spatial_score(self, from_camera: int, 
                             to_camera: int,
                             time_diff: float) -> float:
        """
        Compute spatial consistency score between two cameras.
        
        Returns:
            Score between 0 and 1
        """
        transition = self.get_transition(from_camera, to_camera)
        if not transition:
            return 0.0
        
        # Base score from transition probability
        prob_score = transition.transition_probability
        
        # Time consistency score
        if transition.max_travel_time > 0:
            # Gaussian-like score based on travel time
            expected_time = transition.avg_travel_time
            time_std = transition.std_travel_time or expected_time * 0.2
            
            time_score = np.exp(-0.5 * ((time_diff - expected_time) / time_std) ** 2)
        else:
            time_score = 0.5
        
        # Combine scores
        spatial_score = 0.6 * prob_score + 0.4 * time_score
        
        return float(min(1.0, spatial_score))
    
    def get_adjacency_matrix(self) -> np.ndarray:
        """Get adjacency matrix of camera graph."""
        cameras = sorted(self.graph.nodes())
        n = len(cameras)
        matrix = np.zeros((n, n))
        
        for i, from_cam in enumerate(cameras):
            for j, to_cam in enumerate(cameras):
                if i != j:
                    matrix[i, j] = self.get_transition_probability(from_cam, to_cam)
        
        return matrix
    
    def save_to_database(self):
        """Save camera graph to database."""
        import sqlite3
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create camera topology table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS camera_topology (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_camera INTEGER,
                to_camera INTEGER,
                transition_probability REAL,
                avg_travel_time REAL,
                min_travel_time REAL,
                max_travel_time REAL,
                std_travel_time REAL,
                observation_count INTEGER,
                last_observed DATETIME,
                UNIQUE(from_camera, to_camera)
            )
        ''')
        
        # Store transitions
        for key, transition in self.transitions.items():
            cursor.execute('''
                INSERT OR REPLACE INTO camera_topology
                (from_camera, to_camera, transition_probability,
                 avg_travel_time, min_travel_time, max_travel_time,
                 std_travel_time, observation_count, last_observed)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                transition.from_camera,
                transition.to_camera,
                transition.transition_probability,
                transition.avg_travel_time,
                transition.min_travel_time,
                transition.max_travel_time,
                transition.std_travel_time,
                transition.observation_count,
                transition.last_observed
            ))
        
        conn.commit()
        conn.close()
    
    def _load_from_database(self):
        """Load camera graph from database."""
        import sqlite3
        import os
        
        if not os.path.exists(self.db_path):
            return
        
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Check if table exists
            cursor.execute('''
                SELECT name FROM sqlite_master 
                WHERE type='table' AND name='camera_topology'
            ''')
            
            if cursor.fetchone():
                cursor.execute('''
                    SELECT from_camera, to_camera, transition_probability,
                           avg_travel_time, min_travel_time, max_travel_time,
                           std_travel_time, observation_count, last_observed
                    FROM camera_topology
                ''')
                
                for row in cursor.fetchall():
                    transition = CameraTransition(
                        from_camera=row[0],
                        to_camera=row[1],
                        transition_probability=row[2],
                        avg_travel_time=row[3],
                        min_travel_time=row[4],
                        max_travel_time=row[5],
                        std_travel_time=row[6],
                        observation_count=row[7],
                        last_observed=datetime.fromisoformat(row[8]) if row[8] else None
                    )
                    self.add_transition(row[0], row[1], transition)
            
            conn.close()
            
        except Exception as e:
            print(f"⚠️ Could not load camera topology: {e}")