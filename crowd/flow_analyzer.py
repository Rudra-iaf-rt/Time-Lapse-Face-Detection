# crowd/flow_analyzer.py
import numpy as np
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from collections import defaultdict, deque
import networkx as nx

class FlowAnalyzer:
    """
    Analyze crowd flow and movement patterns.
    """
    
    def __init__(self, config: dict = None):
        self.config = config or {}
        self.flow_data = defaultdict(lambda: deque(maxlen=1000))
        self.transition_matrix = defaultdict(lambda: defaultdict(int))
        self.flow_graph = nx.DiGraph()
        
    def add_flow_observation(self, from_camera: int, to_camera: int,
                            person_id: str, timestamp: datetime,
                            duration: float):
        """
        Add a flow observation (person moving from one camera to another).
        """
        # Store flow data
        self.flow_data[person_id].append({
            'from_camera': from_camera,
            'to_camera': to_camera,
            'timestamp': timestamp,
            'duration': duration
        })
        
        # Update transition matrix
        self.transition_matrix[from_camera][to_camera] += 1
        
        # Update flow graph
        if self.flow_graph.has_edge(from_camera, to_camera):
            current_weight = self.flow_graph[from_camera][to_camera]['weight']
            self.flow_graph[from_camera][to_camera]['weight'] = current_weight + 1
        else:
            self.flow_graph.add_edge(from_camera, to_camera, weight=1)
    
    def get_flow_matrix(self, time_window: int = 3600) -> np.ndarray:
        """
        Get flow transition matrix for a time window.
        """
        cutoff = datetime.now() - timedelta(seconds=time_window)
        
        # Count recent transitions
        recent_transitions = defaultdict(lambda: defaultdict(int))
        
        for person, flows in self.flow_data.items():
            for flow in flows:
                if flow['timestamp'] >= cutoff:
                    recent_transitions[flow['from_camera']][flow['to_camera']] += 1
        
        # Convert to matrix
        cameras = sorted(set(
            list(recent_transitions.keys()) + 
            sum([list(d.keys()) for d in recent_transitions.values()], [])
        ))
        
        n = len(cameras)
        matrix = np.zeros((n, n))
        camera_to_idx = {cam: i for i, cam in enumerate(cameras)}
        
        for from_cam, to_dict in recent_transitions.items():
            for to_cam, count in to_dict.items():
                if from_cam in camera_to_idx and to_cam in camera_to_idx:
                    matrix[camera_to_idx[from_cam], camera_to_idx[to_cam]] = count
        
        # Normalize rows
        row_sums = matrix.sum(axis=1, keepdims=True)
        row_sums[row_sums == 0] = 1
        matrix = matrix / row_sums
        
        return matrix, cameras
    
    def get_flow_rates(self, camera_id: int, 
                       time_window: int = 3600) -> Dict:
        """
        Get flow rates for a camera.
        """
        cutoff = datetime.now() - timedelta(seconds=time_window)
        
        incoming = 0
        outgoing = 0
        
        for person, flows in self.flow_data.items():
            for flow in flows:
                if flow['timestamp'] >= cutoff:
                    if flow['to_camera'] == camera_id:
                        incoming += 1
                    if flow['from_camera'] == camera_id:
                        outgoing += 1
        
        rate_window = time_window / 60  # minutes
        
        return {
            'incoming_rate': incoming / rate_window if rate_window > 0 else 0,
            'outgoing_rate': outgoing / rate_window if rate_window > 0 else 0,
            'net_flow': (incoming - outgoing) / rate_window if rate_window > 0 else 0,
            'total_flow': (incoming + outgoing) / rate_window if rate_window > 0 else 0
        }
    
    def get_busiest_paths(self, top_n: int = 5) -> List[Dict]:
        """
        Get busiest movement paths.
        """
        # Count all transitions
        transitions = defaultdict(int)
        
        for person, flows in self.flow_data.items():
            for flow in flows:
                key = (flow['from_camera'], flow['to_camera'])
                transitions[key] += 1
        
        # Sort by count
        sorted_transitions = sorted(
            transitions.items(),
            key=lambda x: x[1],
            reverse=True
        )
        
        # Get top N
        busiest = []
        for (from_cam, to_cam), count in sorted_transitions[:top_n]:
            # Calculate average duration
            durations = []
            for person, flows in self.flow_data.items():
                for flow in flows:
                    if flow['from_camera'] == from_cam and flow['to_camera'] == to_cam:
                        durations.append(flow['duration'])
            
            avg_duration = np.mean(durations) if durations else 0
            
            busiest.append({
                'from_camera': from_cam,
                'to_camera': to_cam,
                'count': count,
                'avg_duration': avg_duration,
                'frequency': count / len(self.flow_data) if self.flow_data else 0
            })
        
        return busiest
    
    def get_congestion_points(self, time_window: int = 3600) -> List[Dict]:
        """
        Identify congestion points in the flow network.
        """
        cutoff = datetime.now() - timedelta(seconds=time_window)
        
        # Count recent flows through each camera
        camera_throughput = defaultdict(int)
        
        for person, flows in self.flow_data.items():
            for flow in flows:
                if flow['timestamp'] >= cutoff:
                    camera_throughput[flow['from_camera']] += 1
                    camera_throughput[flow['to_camera']] += 1
        
        # Calculate rates
        rate_window = time_window / 60  # minutes
        
        congestion = []
        for camera_id, throughput in camera_throughput.items():
            rate = throughput / rate_window if rate_window > 0 else 0
            
            # Determine congestion level
            if rate > 10:
                level = 'high'
            elif rate > 5:
                level = 'medium'
            else:
                level = 'low'
            
            congestion.append({
                'camera_id': camera_id,
                'throughput': throughput,
                'rate': rate,
                'level': level
            })
        
        # Sort by rate
        congestion.sort(key=lambda x: x['rate'], reverse=True)
        
        return congestion
    
    def predict_flow(self, from_camera: int, 
                     time_horizon: int = 60) -> List[Tuple[int, float]]:
        """
        Predict where people will flow from a camera.
        """
        # Get transition probabilities
        if from_camera not in self.transition_matrix:
            return []
        
        # Get recent transitions
        cutoff = datetime.now() - timedelta(seconds=time_horizon)
        recent_counts = defaultdict(int)
        total_recent = 0
        
        for person, flows in self.flow_data.items():
            for flow in flows:
                if (flow['timestamp'] >= cutoff and 
                    flow['from_camera'] == from_camera):
                    recent_counts[flow['to_camera']] += 1
                    total_recent += 1
        
        if total_recent == 0:
            # Use historical probabilities
            predictions = []
            total = sum(self.transition_matrix[from_camera].values())
            if total > 0:
                for to_camera, count in self.transition_matrix[from_camera].items():
                    predictions.append((to_camera, count / total))
            return sorted(predictions, key=lambda x: x[1], reverse=True)
        
        # Use recent data with smoothing
        predictions = []
        for to_camera, count in recent_counts.items():
            prob = count / total_recent
            # Smooth with historical data
            historical_total = sum(self.transition_matrix[from_camera].values())
            if historical_total > 0:
                historical_prob = self.transition_matrix[from_camera][to_camera] / historical_total
                prob = 0.7 * prob + 0.3 * historical_prob
            
            predictions.append((to_camera, prob))
        
        return sorted(predictions, key=lambda x: x[1], reverse=True)