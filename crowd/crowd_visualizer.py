# crowd/crowd_visualizer.py
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Optional, Any
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import seaborn as sns

class CrowdVisualizer:
    """
    Visualize crowd analytics and metrics.
    """
    
    def __init__(self, figsize: tuple = (15, 10)):
        self.figsize = figsize
        self.cmap = 'YlOrRd'
    
    def visualize_occupancy(self, camera_id: int, 
                           history: List[Dict],
                           save_path: Optional[str] = None):
        """
        Visualize occupancy over time.
        """
        if not history:
            print("No occupancy data to visualize")
            return
        
        fig, axes = plt.subplots(2, 2, figsize=self.figsize)
        
        # 1. Occupancy over time
        timestamps = [h['timestamp'] for h in history]
        occupancies = [h['occupancy'] for h in history]
        
        axes[0, 0].plot(timestamps, occupancies, 'b-', linewidth=2)
        axes[0, 0].set_title(f'Camera {camera_id} - Occupancy Over Time')
        axes[0, 0].set_xlabel('Time')
        axes[0, 0].set_ylabel('Occupancy')
        axes[0, 0].grid(True, alpha=0.3)
        
        # 2. Occupancy distribution
        axes[0, 1].hist(occupancies, bins=20, edgecolor='black', 
                       color='skyblue', alpha=0.7)
        axes[0, 1].set_title('Occupancy Distribution')
        axes[0, 1].set_xlabel('Occupancy')
        axes[0, 1].set_ylabel('Frequency')
        
        # 3. Capacity utilization
        capacity = self.config.get('camera_capacities', {}).get(camera_id, 100)
        utilization = [o / capacity * 100 for o in occupancies]
        
        axes[1, 0].plot(timestamps, utilization, 'r-', linewidth=2)
        axes[1, 0].axhline(y=80, color='orange', linestyle='--', label='Warning (80%)')
        axes[1, 0].axhline(y=95, color='red', linestyle='--', label='Critical (95%)')
        axes[1, 0].set_title('Capacity Utilization')
        axes[1, 0].set_xlabel('Time')
        axes[1, 0].set_ylabel('Utilization (%)')
        axes[1, 0].legend()
        axes[1, 0].grid(True, alpha=0.3)
        
        # 4. Hourly pattern (if enough data)
        if len(history) >= 24:
            hourly_avg = {}
            for h in history:
                hour = h['timestamp'].hour
                if hour not in hourly_avg:
                    hourly_avg[hour] = []
                hourly_avg[hour].append(h['occupancy'])
            
            hours = sorted(hourly_avg.keys())
            averages = [np.mean(hourly_avg[h]) for h in hours]
            
            axes[1, 1].bar(hours, averages, color='lightgreen', alpha=0.7)
            axes[1, 1].set_title('Average Hourly Occupancy')
            axes[1, 1].set_xlabel('Hour')
            axes[1, 1].set_ylabel('Average Occupancy')
            axes[1, 1].grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Occupancy visualization saved to {save_path}")
        
        plt.show()
    
    def visualize_density(self, camera_id: int,
                         density_map: np.ndarray,
                         save_path: Optional[str] = None):
        """
        Visualize density heatmap.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        im = ax.imshow(density_map, cmap=self.cmap, origin='lower',
                      extent=[0, 1, 0, 1])
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Density', fontsize=12)
        
        # Add hotspots
        from .density_estimator import DensityEstimator
        estimator = DensityEstimator()
        hotspots = estimator.get_hotspots(density_map)
        
        if hotspots:
            for i, j in hotspots:
                x = j / density_map.shape[1]
                y = i / density_map.shape[0]
                ax.scatter(x, y, color='red', s=100, marker='x', 
                          linewidths=2, label='Hotspot')
        
        ax.set_title(f'Camera {camera_id} - Density Heatmap', fontsize=14)
        ax.set_xlabel('X Position', fontsize=12)
        ax.set_ylabel('Y Position', fontsize=12)
        ax.legend()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Density visualization saved to {save_path}")
        
        plt.show()
    
    def visualize_flow(self, flow_matrix: np.ndarray,
                       camera_ids: List[int],
                       save_path: Optional[str] = None):
        """
        Visualize flow matrix.
        """
        fig, ax = plt.subplots(figsize=(10, 8))
        
        # Create heatmap
        im = ax.imshow(flow_matrix, cmap='Blues', aspect='auto')
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Flow Probability', fontsize=12)
        
        # Add labels
        ax.set_xticks(np.arange(len(camera_ids)))
        ax.set_yticks(np.arange(len(camera_ids)))
        ax.set_xticklabels([f'Cam {c}' for c in camera_ids], rotation=45, ha='right')
        ax.set_yticklabels([f'Cam {c}' for c in camera_ids])
        
        # Add text annotations
        for i in range(len(camera_ids)):
            for j in range(len(camera_ids)):
                if flow_matrix[i, j] > 0.05:
                    text = ax.text(j, i, f'{flow_matrix[i, j]:.2f}',
                                 ha="center", va="center", 
                                 color="black" if flow_matrix[i, j] < 0.5 else "white",
                                 fontsize=8)
        
        ax.set_title('Crowd Flow Matrix', fontsize=14)
        ax.set_xlabel('Destination Camera', fontsize=12)
        ax.set_ylabel('Source Camera', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Flow visualization saved to {save_path}")
        
        plt.show()
    
    def visualize_crowd_dashboard(self, metrics: Dict,
                                  save_path: Optional[str] = None):
        """
        Create comprehensive crowd dashboard.
        """
        fig = make_subplots(
            rows=3, cols=2,
            subplot_titles=('Current Occupancy', 'Camera Status',
                          'Hourly Trend', 'Entry/Exit Rates',
                          'Flow Summary', 'Alerts')
        )
        
        # 1. Current occupancy (bar chart)
        cameras = list(metrics.get('current_occupancy', {}).keys())
        occupancies = list(metrics.get('current_occupancy', {}).values())
        capacities = [metrics.get('capacities', {}).get(c, 100) for c in cameras]
        
        fig.add_trace(
            go.Bar(x=[f'Cam {c}' for c in cameras], 
                  y=occupancies, name='Occupancy',
                  marker_color='lightblue'),
            row=1, col=1
        )
        
        # 2. Camera status (utilization)
        utilization = [o / c * 100 for o, c in zip(occupancies, capacities)]
        colors = ['green' if u < 70 else 'orange' if u < 90 else 'red' for u in utilization]
        
        fig.add_trace(
            go.Bar(x=[f'Cam {c}' for c in cameras], 
                  y=utilization, name='Utilization %',
                  marker_color=colors),
            row=1, col=2
        )
        
        # 3. Hourly trend
        hourly_data = metrics.get('hourly_trend', {})
        if hourly_data:
            hours = list(hourly_data.keys())
            values = list(hourly_data.values())
            
            fig.add_trace(
                go.Scatter(x=hours, y=values, mode='lines+markers',
                          name='Hourly Avg', line=dict(color='blue')),
                row=2, col=1
            )
        
        # 4. Entry/Exit rates
        entry_rates = metrics.get('entry_rates', {})
        exit_rates = metrics.get('exit_rates', {})
        
        fig.add_trace(
            go.Bar(x=[f'Cam {c}' for c in entry_rates.keys()],
                  y=list(entry_rates.values()), name='Entry Rate',
                  marker_color='green'),
            row=2, col=2
        )
        fig.add_trace(
            go.Bar(x=[f'Cam {c}' for c in exit_rates.keys()],
                  y=list(exit_rates.values()), name='Exit Rate',
                  marker_color='red'),
            row=2, col=2
        )
        
        # 5. Flow summary
        flows = metrics.get('flow_summary', [])
        if flows:
            flow_names = [f"{f['from']}→{f['to']}" for f in flows[:5]]
            flow_counts = [f['count'] for f in flows[:5]]
            
            fig.add_trace(
                go.Bar(x=flow_names, y=flow_counts, name='Flows',
                      marker_color='purple'),
                row=3, col=1
            )
        
        # 6. Alerts
        alerts = metrics.get('alerts', [])
        if alerts:
            alert_text = "<br>".join([a['message'] for a in alerts[:5]])
            fig.add_annotation(
                text=f"Alerts:<br>{alert_text}",
                xref="x domain", yref="y domain",
                x=0.5, y=0.5,
                showarrow=False,
                font=dict(size=12, color='red' if alerts else 'green')
            )
        
        fig.update_layout(height=800, showlegend=True,
                         title_text="Crowd Intelligence Dashboard")
        
        if save_path:
            fig.write_html(save_path)
            print(f"✅ Crowd dashboard saved to {save_path}")
        
        fig.show()