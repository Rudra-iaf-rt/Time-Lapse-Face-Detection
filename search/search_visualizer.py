# search/search_visualizer.py
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class SearchVisualizer:
    """
    Visualize search results.
    """
    
    def __init__(self, figsize: tuple = (12, 8)):
        self.figsize = figsize
    
    def visualize_results(self, results: Dict, save_path: Optional[str] = None):
        """
        Visualize search results.
        """
        if not results or not results.get('results'):
            print("No results to visualize")
            return
        
        result_type = results.get('result_type', 'unknown')
        
        if result_type == 'persons':
            self._visualize_persons(results, save_path)
        elif result_type == 'events':
            self._visualize_events(results, save_path)
        elif result_type == 'transitions':
            self._visualize_transitions(results, save_path)
        else:
            self._visualize_generic(results, save_path)
    
    def _visualize_persons(self, results: Dict, save_path: Optional[str] = None):
        """Visualize person search results."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        aggregated = results.get('aggregated', {})
        person_results = results.get('results', [])
        
        # 1. Camera visits
        camera_visits = aggregated.get('camera_visits', {})
        if camera_visits:
            cameras = list(camera_visits.keys())
            counts = list(camera_visits.values())
            axes[0, 0].bar([f'Cam {c}' for c in cameras], counts)
            axes[0, 0].set_title('Camera Visits')
            axes[0, 0].set_xlabel('Camera')
            axes[0, 0].set_ylabel('Visit Count')
        
        # 2. Time distribution
        time_dist = aggregated.get('time_distribution', {})
        if time_dist:
            hours = list(time_dist.keys())
            counts = list(time_dist.values())
            axes[0, 1].bar(hours, counts)
            axes[0, 1].set_title('Hourly Activity')
            axes[0, 1].set_xlabel('Hour')
            axes[0, 1].set_ylabel('Count')
        
        # 3. Duration distribution
        durations = [r.get('total_duration', 0) for r in person_results]
        if durations:
            axes[1, 0].hist(durations, bins=20, edgecolor='black')
            axes[1, 0].set_title('Duration Distribution')
            axes[1, 0].set_xlabel('Duration (s)')
            axes[1, 0].set_ylabel('Count')
        
        # 4. Confidence distribution
        confidences = [r.get('confidence', 0) for r in person_results]
        if confidences:
            axes[1, 1].hist(confidences, bins=20, edgecolor='black', color='green')
            axes[1, 1].set_title('Confidence Distribution')
            axes[1, 1].set_xlabel('Confidence')
            axes[1, 1].set_ylabel('Count')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to {save_path}")
        
        plt.show()
    
    def _visualize_events(self, results: Dict, save_path: Optional[str] = None):
        """Visualize event search results."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        aggregated = results.get('aggregated', {})
        
        # 1. Event types
        event_types = aggregated.get('event_types', {})
        if event_types:
            types = list(event_types.keys())
            counts = list(event_types.values())
            axes[0, 0].bar(types, counts, color='skyblue')
            axes[0, 0].set_title('Event Types')
            axes[0, 0].set_xlabel('Event Type')
            axes[0, 0].set_ylabel('Count')
            plt.setp(axes[0, 0].get_xticklabels(), rotation=45, ha='right')
        
        # 2. Camera distribution
        camera_dist = aggregated.get('camera_distribution', {})
        if camera_dist:
            cameras = list(camera_dist.keys())
            counts = list(camera_dist.values())
            axes[0, 1].bar([f'Cam {c}' for c in cameras], counts, color='lightcoral')
            axes[0, 1].set_title('Events by Camera')
            axes[0, 1].set_xlabel('Camera')
            axes[0, 1].set_ylabel('Event Count')
        
        # 3. Time distribution
        time_dist = aggregated.get('time_distribution', {})
        if time_dist:
            hours = list(time_dist.keys())
            counts = list(time_dist.values())
            axes[1, 0].bar(hours, counts, color='lightgreen')
            axes[1, 0].set_title('Events by Hour')
            axes[1, 0].set_xlabel('Hour')
            axes[1, 0].set_ylabel('Event Count')
        
        # 4. Person distribution (top 10)
        person_dist = aggregated.get('person_distribution', {})
        if person_dist:
            persons = list(person_dist.keys())[:10]
            counts = [person_dist[p] for p in persons]
            axes[1, 1].barh(persons, counts, color='plum')
            axes[1, 1].set_title('Events by Person (Top 10)')
            axes[1, 1].set_xlabel('Event Count')
            axes[1, 1].set_ylabel('Person ID')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to {save_path}")
        
        plt.show()
    
    def _visualize_transitions(self, results: Dict, save_path: Optional[str] = None):
        """Visualize transition search results."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        aggregated = results.get('aggregated', {})
        transition_results = results.get('results', [])
        
        # 1. Transition counts (top 10)
        transitions = aggregated.get('transition_counts', {})
        if transitions:
            items = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:10]
            names = [t[0] for t in items]
            counts = [t[1] for t in items]
            axes[0, 0].barh(names, counts, color='orchid')
            axes[0, 0].set_title('Top Transitions')
            axes[0, 0].set_xlabel('Count')
        
        # 2. Duration distribution
        durations = [r.get('duration', 0) for r in transition_results]
        if durations:
            axes[0, 1].hist(durations, bins=20, edgecolor='black', color='gold')
            axes[0, 1].set_title('Transition Duration')
            axes[0, 1].set_xlabel('Duration (s)')
            axes[0, 1].set_ylabel('Count')
        
        # 3. Confidence distribution
        confidences = [r.get('confidence', 0) for r in transition_results]
        if confidences:
            axes[1, 0].hist(confidences, bins=20, edgecolor='black', color='teal')
            axes[1, 0].set_title('Transition Confidence')
            axes[1, 0].set_xlabel('Confidence')
            axes[1, 0].set_ylabel('Count')
        
        # 4. Person distribution (top 10)
        person_dist = aggregated.get('person_distribution', {})
        if person_dist:
            persons = list(person_dist.keys())[:10]
            counts = [person_dist[p] for p in persons]
            axes[1, 1].barh(persons, counts, color='coral')
            axes[1, 1].set_title('Transitions by Person (Top 10)')
            axes[1, 1].set_xlabel('Transition Count')
            axes[1, 1].set_ylabel('Person ID')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to {save_path}")
        
        plt.show()
    
    def _visualize_generic(self, results: Dict, save_path: Optional[str] = None):
        """Generic visualization for unknown result types."""
        fig, ax = plt.subplots(figsize=self.figsize)
        
        result_count = len(results.get('results', []))
        ax.text(0.5, 0.5, f'Search Results\n\nTotal: {result_count}',
                ha='center', va='center', fontsize=20)
        ax.set_xlim(0, 1)
        ax.set_ylim(0, 1)
        ax.axis('off')
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Visualization saved to {save_path}")
        
        plt.show()
    
    def visualize_timeline_search(self, timeline_results: List[Dict],
                                  save_path: Optional[str] = None):
        """
        Visualize timeline search results.
        """
        if not timeline_results:
            print("No timeline results to visualize")
            return
        
        fig, ax = plt.subplots(figsize=(15, 8))
        
        # Sort by time
        sorted_results = sorted(timeline_results, 
                              key=lambda x: x.get('timestamp', datetime.min))
        
        # Create timeline view
        for i, result in enumerate(sorted_results):
            timestamp = result.get('timestamp')
            camera_id = result.get('camera_id', -1)
            global_id = result.get('global_id', '')
            
            if timestamp:
                if isinstance(timestamp, str):
                    timestamp = datetime.fromisoformat(timestamp)
                
                y_pos = i * 0.5
                ax.scatter(timestamp, y_pos, s=100, 
                          label=f'Cam {camera_id}')
                ax.text(timestamp, y_pos + 0.1, 
                       f'{global_id[-8:]}\nCam {camera_id}',
                       ha='center', fontsize=8)
        
        ax.set_xlabel('Time')
        ax.set_ylabel('Event Index')
        ax.set_title('Timeline Search Results')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Timeline search saved to {save_path}")
        
        plt.show()