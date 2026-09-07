# behavior/behavior_visualizer.py
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import networkx as nx

class BehaviorVisualizer:
    """
    Visualize behavioral patterns and anomalies.
    """
    
    def __init__(self, figsize: tuple = (14, 10)):
        self.figsize = figsize
    
    def visualize_behavior_profile(self, profile: Dict, 
                                   save_path: Optional[str] = None):
        """Visualize a behavioral profile."""
        fig, axes = plt.subplots(2, 3, figsize=self.figsize)
        
        # 1. Activity patterns
        activity = profile.get('activity_patterns', {})
        if activity:
            hours = sorted(activity.keys())
            values = [activity[h] for h in hours]
            axes[0, 0].bar(hours, values, color='skyblue')
            axes[0, 0].set_title('Hourly Activity')
            axes[0, 0].set_xlabel('Hour')
            axes[0, 0].set_ylabel('Activity Level')
        
        # 2. Camera preferences
        cameras = profile.get('camera_preferences', {})
        if cameras:
            cam_ids = sorted(cameras.keys())
            values = [cameras[c] for c in cam_ids]
            axes[0, 1].bar([f'Cam {c}' for c in cam_ids], values, color='lightcoral')
            axes[0, 1].set_title('Camera Preferences')
            axes[0, 1].set_xlabel('Camera')
            axes[0, 1].set_ylabel('Visit Frequency')
        
        # 3. Dwell patterns
        dwell = profile.get('dwell_patterns', {})
        if dwell:
            cam_ids = sorted(dwell.keys())
            values = [dwell[c] for c in cam_ids]
            axes[0, 2].bar([f'Cam {c}' for c in cam_ids], values, color='lightgreen')
            axes[0, 2].set_title('Dwell Time by Camera')
            axes[0, 2].set_xlabel('Camera')
            axes[0, 2].set_ylabel('Avg Dwell Time (s)')
        
        # 4. Transition patterns
        transitions = profile.get('transition_patterns', {})
        if transitions:
            # Show top 5 transitions
            items = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:5]
            names = [t[0] for t in items]
            values = [t[1] for t in items]
            axes[1, 0].barh(names, values, color='orchid')
            axes[1, 0].set_title('Top Transitions')
            axes[1, 0].set_xlabel('Frequency')
        
        # 5. Route visualization
        route = profile.get('typical_route', [])
        if route:
            axes[1, 1].plot(range(len(route)), route, 'o-', 
                           linewidth=2, markersize=10, color='blue')
            axes[1, 1].set_title('Typical Route')
            axes[1, 1].set_xlabel('Step')
            axes[1, 1].set_ylabel('Camera ID')
            axes[1, 1].grid(True, alpha=0.3)
        
        # 6. Summary stats
        stats_text = f"""
        Person ID: {profile.get('global_id', 'N/A')}
        Visit Frequency: {profile.get('visit_frequency', 0):.2f}/day
        Typical Duration: {profile.get('typical_duration', 0):.1f}s
        Preferred Hours: {', '.join(map(str, profile.get('preferred_hours', [])))}
        Last Updated: {profile.get('last_updated', 'N/A')[:19]}
        """
        axes[1, 2].text(0.1, 0.5, stats_text, transform=axes[1, 2].transAxes,
                       fontsize=10, verticalalignment='center')
        axes[1, 2].axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Behavior profile saved to {save_path}")
        
        plt.show()
    
    def visualize_anomalies(self, anomalies: List[Dict], 
                           save_path: Optional[str] = None):
        """Visualize detected anomalies."""
        if not anomalies:
            print("No anomalies to visualize")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        # 1. Anomaly types
        types = [a.get('type', 'unknown') for a in anomalies]
        type_counts = {t: types.count(t) for t in set(types)}
        
        if type_counts:
            axes[0, 0].bar(type_counts.keys(), type_counts.values(), color='salmon')
            axes[0, 0].set_title('Anomaly Types')
            axes[0, 0].set_xlabel('Type')
            axes[0, 0].set_ylabel('Count')
            plt.setp(axes[0, 0].get_xticklabels(), rotation=45, ha='right')
        
        # 2. Severity distribution
        severities = [a.get('severity', 'low') for a in anomalies]
        severity_counts = {s: severities.count(s) for s in set(severities)}
        
        if severity_counts:
            colors = {'high': 'red', 'medium': 'orange', 'low': 'yellow'}
            axes[0, 1].bar(severity_counts.keys(), severity_counts.values(),
                          color=[colors.get(s, 'gray') for s in severity_counts.keys()])
            axes[0, 1].set_title('Anomaly Severity')
            axes[0, 1].set_xlabel('Severity')
            axes[0, 1].set_ylabel('Count')
        
        # 3. Confidence distribution
        confidences = [a.get('confidence', 0) for a in anomalies]
        if confidences:
            axes[1, 0].hist(confidences, bins=20, edgecolor='black', color='lightblue')
            axes[1, 0].set_title('Anomaly Confidence')
            axes[1, 0].set_xlabel('Confidence')
            axes[1, 0].set_ylabel('Count')
        
        # 4. Timeline of anomalies
        timestamps = []
        for a in anomalies:
            ts = a.get('timestamp')
            if ts:
                if isinstance(ts, str):
                    ts = datetime.fromisoformat(ts)
                timestamps.append(ts)
        
        if timestamps:
            axes[1, 1].scatter(timestamps, [1] * len(timestamps),
                              s=[a.get('confidence', 0) * 100 for a in anomalies],
                              c=['red' if a.get('severity') == 'high' else 
                                 'orange' if a.get('severity') == 'medium' else 'yellow'
                                 for a in anomalies],
                              alpha=0.6)
            axes[1, 1].set_title('Anomaly Timeline')
            axes[1, 1].set_xlabel('Time')
            axes[1, 1].set_ylabel('')
            axes[1, 1].set_yticks([])
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Anomaly visualization saved to {save_path}")
        
        plt.show()
    
    def visualize_behavior_patterns(self, patterns: Dict,
                                   save_path: Optional[str] = None):
        """Visualize behavioral patterns."""
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        # 1. Common routes
        routes = patterns.get('common_routes', [])
        if routes:
            route_names = [' → '.join(map(str, r['route'])) for r in routes[:5]]
            counts = [r['count'] for r in routes[:5]]
            axes[0, 0].barh(route_names, counts, color='lightblue')
            axes[0, 0].set_title('Common Routes')
            axes[0, 0].set_xlabel('Frequency')
        
        # 2. Camera usage
        camera_usage = patterns.get('camera_usage', {})
        if camera_usage:
            cameras = sorted(camera_usage.keys())
            visit_counts = [camera_usage[c]['visit_count'] for c in cameras]
            axes[0, 1].bar([f'Cam {c}' for c in cameras], visit_counts, color='lightcoral')
            axes[0, 1].set_title('Camera Usage')
            axes[0, 1].set_xlabel('Camera')
            axes[0, 1].set_ylabel('Visit Count')
        
        # 3. Peak hours
        peak_hours = patterns.get('peak_hours', {})
        hourly_dist = peak_hours.get('hourly_distribution', {})
        if hourly_dist:
            hours = sorted(hourly_dist.keys())
            counts = [hourly_dist[h] for h in hours]
            axes[1, 0].bar(hours, counts, color='lightgreen')
            axes[1, 0].set_title('Hourly Activity')
            axes[1, 0].set_xlabel('Hour')
            axes[1, 0].set_ylabel('Activity Count')
        
        # 4. Crowd patterns
        crowd_patterns = patterns.get('crowd_patterns', [])
        if crowd_patterns:
            times = [p['time'] for p in crowd_patterns[:10]]
            counts = [p['total_people'] for p in crowd_patterns[:10]]
            axes[1, 1].bar(times, counts, color='plum')
            axes[1, 1].set_title('Crowd Patterns')
            axes[1, 1].set_xlabel('Time')
            axes[1, 1].set_ylabel('People')
            plt.setp(axes[1, 1].get_xticklabels(), rotation=45, ha='right')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Behavior patterns saved to {save_path}")
        
        plt.show()
    
    def visualize_behavior_plotly(self, profile: Dict, 
                                  save_path: Optional[str] = None):
        """Create interactive behavior visualization using Plotly."""
        fig = make_subplots(rows=2, cols=2,
                           subplot_titles=('Activity Patterns', 'Camera Preferences',
                                         'Dwell Times', 'Transition Patterns'))
        
        # 1. Activity patterns
        activity = profile.get('activity_patterns', {})
        if activity:
            hours = sorted(activity.keys())
            values = [activity[h] for h in hours]
            fig.add_trace(
                go.Bar(x=hours, y=values, name='Activity', marker_color='skyblue'),
                row=1, col=1
            )
        
        # 2. Camera preferences
        cameras = profile.get('camera_preferences', {})
        if cameras:
            cam_ids = sorted(cameras.keys())
            values = [cameras[c] for c in cam_ids]
            fig.add_trace(
                go.Bar(x=[f'Cam {c}' for c in cam_ids], y=values, 
                       name='Preferences', marker_color='lightcoral'),
                row=1, col=2
            )
        
        # 3. Dwell times
        dwell = profile.get('dwell_patterns', {})
        if dwell:
            cam_ids = sorted(dwell.keys())
            values = [dwell[c] for c in cam_ids]
            fig.add_trace(
                go.Bar(x=[f'Cam {c}' for c in cam_ids], y=values,
                       name='Dwell', marker_color='lightgreen'),
                row=2, col=1
            )
        
        # 4. Transitions
        transitions = profile.get('transition_patterns', {})
        if transitions:
            items = sorted(transitions.items(), key=lambda x: x[1], reverse=True)[:5]
            names = [f"{k[0]}→{k[1]}" for k, _ in items]
            values = [v for _, v in items]
            fig.add_trace(
                go.Bar(x=names, y=values, name='Transitions', marker_color='orchid'),
                row=2, col=2
            )
        
        fig.update_layout(height=600, showlegend=False,
                         title=f"Behavior Profile: {profile.get('global_id', 'Unknown')}")
        
        if save_path:
            fig.write_html(save_path)
            print(f"✅ Interactive behavior visualization saved to {save_path}")
        
        fig.show()