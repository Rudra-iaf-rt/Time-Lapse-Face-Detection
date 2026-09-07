# timeline/timeline_visualizer.py
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.colors import to_rgba
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from .timeline_builder import PersonTimeline

class TimelineVisualizer:
    """
    Visualize person timelines.
    """
    
    def __init__(self, figsize: tuple = (15, 10)):
        self.figsize = figsize
        self.camera_colors = {}
    
    def visualize_timeline(self, timeline: PersonTimeline,
                          save_path: Optional[str] = None):
        """
        Visualize a single person's timeline.
        """
        if not timeline.segments:
            print("No segments to visualize")
            return
        
        fig, (ax1, ax2) = plt.subplots(2, 1, figsize=self.figsize, 
                                       gridspec_kw={'height_ratios': [3, 1]})
        
        # Get unique cameras
        cameras = sorted(timeline.cameras_visited)
        camera_to_y = {cam: i for i, cam in enumerate(cameras)}
        
        # Plot segments as horizontal bars
        for segment in timeline.segments:
            y_pos = camera_to_y[segment.camera_id]
            color = self._get_camera_color(segment.camera_id)
            
            # Draw segment
            ax1.barh(y_pos, segment.duration, 
                    left=(segment.start_time - timeline.first_seen).total_seconds(),
                    height=0.6, color=color, alpha=0.7,
                    edgecolor='black', linewidth=1)
            
            # Add quality indicator
            if segment.confidence > 0.7:
                edge_color = 'green'
            elif segment.confidence > 0.4:
                edge_color = 'orange'
            else:
                edge_color = 'red'
            
            ax1.barh(y_pos, segment.duration,
                    left=(segment.start_time - timeline.first_seen).total_seconds(),
                    height=0.2, color=edge_color, alpha=0.3)
        
        # Add events as markers
        for event in timeline.events:
            if event.event_type == 'entry':
                marker = '^'
                color = 'green'
            elif event.event_type == 'exit':
                marker = 'v'
                color = 'red'
            elif event.event_type == 'movement':
                marker = '>'
                color = 'blue'
            else:
                marker = 'o'
                color = 'gray'
            
            x_pos = (event.timestamp - timeline.first_seen).total_seconds()
            y_pos = camera_to_y.get(event.camera_id, 0)
            
            ax1.scatter(x_pos, y_pos, marker=marker, color=color, s=100, zorder=5)
        
        # Formatting
        ax1.set_yticks(range(len(cameras)))
        ax1.set_yticklabels([f'Camera {cam}' for cam in cameras])
        ax1.set_xlabel('Time (seconds from first seen)')
        ax1.set_ylabel('Camera')
        ax1.set_title(f'Timeline: {timeline.global_id}\n'
                     f'First seen: {timeline.first_seen.strftime("%H:%M:%S") if timeline.first_seen else "N/A"} | '
                     f'Duration: {timeline.total_duration:.1f}s | '
                     f'Cameras visited: {len(timeline.cameras_visited)}')
        ax1.grid(True, alpha=0.3)
        
        # Second subplot: Camera visits summary
        dwell_times = timeline.get_camera_dwell_times()
        cameras_list = sorted(dwell_times.keys())
        durations = [dwell_times[cam] for cam in cameras_list]
        colors = [self._get_camera_color(cam) for cam in cameras_list]
        
        ax2.bar([f'Cam {cam}' for cam in cameras_list], durations, color=colors, alpha=0.7)
        ax2.set_xlabel('Camera')
        ax2.set_ylabel('Total Dwell Time (s)')
        ax2.set_title('Dwell Time by Camera')
        ax2.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Timeline saved to {save_path}")
        
        plt.show()
    
    def visualize_multiple_timelines(self, timelines: List[PersonTimeline],
                                     save_path: Optional[str] = None,
                                     max_timelines: int = 5):
        """
        Visualize multiple timelines side by side.
        """
        if not timelines:
            print("No timelines to visualize")
            return
        
        n = min(len(timelines), max_timelines)
        fig, axes = plt.subplots(n, 1, figsize=(self.figsize[0], self.figsize[1] * n / 2))
        
        if n == 1:
            axes = [axes]
        
        # Get global time range
        all_first_seen = [tl.first_seen for tl in timelines if tl.first_seen]
        all_last_seen = [tl.last_seen for tl in timelines if tl.last_seen]
        if not all_first_seen or not all_last_seen:
            print("No valid timelines")
            return
        
        global_start = min(all_first_seen)
        global_end = max(all_last_seen)
        
        for idx, timeline in enumerate(timelines[:n]):
            ax = axes[idx]
            
            # Get unique cameras for this timeline
            cameras = sorted(timeline.cameras_visited)
            camera_to_y = {cam: i for i, cam in enumerate(cameras)}
            
            # Plot segments
            for segment in timeline.segments:
                y_pos = camera_to_y[segment.camera_id]
                color = self._get_camera_color(segment.camera_id)
                
                ax.barh(y_pos, segment.duration,
                       left=(segment.start_time - global_start).total_seconds(),
                       height=0.6, color=color, alpha=0.7,
                       edgecolor='black', linewidth=1)
            
            # Formatting
            ax.set_yticks(range(len(cameras)))
            ax.set_yticklabels([f'Cam {cam}' for cam in cameras])
            ax.set_xlim(0, (global_end - global_start).total_seconds())
            ax.set_ylabel(timeline.global_id[-8:])
            ax.grid(True, alpha=0.3)
            
            # Add title with summary
            ax.set_title(f'{timeline.global_id} | '
                        f'Duration: {timeline.total_duration:.1f}s | '
                        f'Cameras: {len(timeline.cameras_visited)}')
        
        fig.suptitle('Multiple Person Timelines', fontsize=16, fontweight='bold')
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Multiple timelines saved to {save_path}")
        
        plt.show()
    
    def visualize_route(self, route: List[int],
                       start_time: datetime,
                       save_path: Optional[str] = None):
        """
        Visualize a movement route.
        """
        fig, ax = plt.subplots(figsize=(10, 6))
        
        # Create a path visualization
        y_positions = list(range(len(route)))
        
        # Draw path
        ax.plot(y_positions, route, 'o-', linewidth=3, markersize=10,
                markerfacecolor='blue', markeredgecolor='black',
                markeredgewidth=2)
        
        # Add labels
        for i, cam in enumerate(route):
            ax.annotate(f'Cam {cam}', (i, cam), 
                       xytext=(0, 10), textcoords='offset points',
                       ha='center', fontsize=12, fontweight='bold')
        
        ax.set_xlabel('Step')
        ax.set_ylabel('Camera ID')
        ax.set_title(f'Movement Route\nStart: {start_time.strftime("%H:%M:%S")}')
        ax.grid(True, alpha=0.3)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Route saved to {save_path}")
        
        plt.show()
    
    def visualize_timeline_plotly(self, timeline: PersonTimeline,
                                  save_path: Optional[str] = None):
        """
        Create interactive timeline using Plotly.
        """
        if not timeline.segments:
            print("No segments to visualize")
            return
        
        # Prepare data
        cameras = sorted(timeline.cameras_visited)
        camera_to_y = {cam: i for i, cam in enumerate(cameras)}
        
        fig = make_subplots(rows=2, cols=1,
                           subplot_titles=('Timeline View', 'Camera Dwell Times'),
                           row_heights=[0.7, 0.3])
        
        # Add segments
        for segment in timeline.segments:
            y_pos = camera_to_y[segment.camera_id]
            
            # Convert to seconds from start
            x_start = (segment.start_time - timeline.first_seen).total_seconds()
            x_end = x_start + segment.duration
            
            fig.add_trace(
                go.Scatter(
                    x=[x_start, x_end, x_end, x_start, x_start],
                    y=[y_pos-0.3, y_pos-0.3, y_pos+0.3, y_pos+0.3, y_pos-0.3],
                    fill='toself',
                    name=f'Cam {segment.camera_id}',
                    hoverinfo='text',
                    hovertext=f'Camera: {segment.camera_id}<br>'
                              f'Duration: {segment.duration:.1f}s<br>'
                              f'Confidence: {segment.confidence:.2f}',
                    showlegend=False
                ),
                row=1, col=1
            )
        
        # Add events
        event_colors = {
            'entry': 'green',
            'exit': 'red',
            'movement': 'blue',
            'dwell': 'orange'
        }
        
        for event in timeline.events:
            if event.camera_id in camera_to_y:
                x_pos = (event.timestamp - timeline.first_seen).total_seconds()
                y_pos = camera_to_y[event.camera_id]
                
                fig.add_trace(
                    go.Scatter(
                        x=[x_pos],
                        y=[y_pos],
                        mode='markers',
                        marker=dict(
                            symbol='triangle-up' if event.event_type == 'entry' else
                                   'triangle-down' if event.event_type == 'exit' else
                                   'circle',
                            size=15,
                            color=event_colors.get(event.event_type, 'gray')
                        ),
                        name=event.event_type,
                        hoverinfo='text',
                        hovertext=f'Event: {event.event_type}<br>'
                                  f'Time: {event.timestamp.strftime("%H:%M:%S")}'
                    ),
                    row=1, col=1
                )
        
        # Camera dwell times
        dwell_times = timeline.get_camera_dwell_times()
        cameras_list = sorted(dwell_times.keys())
        durations = [dwell_times[cam] for cam in cameras_list]
        
        fig.add_trace(
            go.Bar(
                x=[f'Cam {cam}' for cam in cameras_list],
                y=durations,
                marker_color='lightblue',
                marker_line_color='black',
                marker_line_width=1,
                name='Dwell Time'
            ),
            row=2, col=1
        )
        
        # Update layout
        fig.update_layout(
            title=f'Timeline: {timeline.global_id}',
            height=600,
            showlegend=False,
            hovermode='closest'
        )
        
        fig.update_xaxes(title_text='Time (seconds)', row=1, col=1)
        fig.update_yaxes(title_text='Camera', row=1, col=1,
                        tickvals=list(camera_to_y.values()),
                        ticktext=[f'Cam {cam}' for cam in camera_to_y.keys()])
        
        fig.update_xaxes(title_text='Camera', row=2, col=1)
        fig.update_yaxes(title_text='Dwell Time (s)', row=2, col=1)
        
        if save_path:
            fig.write_html(save_path)
            print(f"✅ Interactive timeline saved to {save_path}")
        
        fig.show()
    
    def _get_camera_color(self, camera_id: int) -> str:
        """Get consistent color for a camera."""
        if camera_id not in self.camera_colors:
            # Generate color from camera ID
            colors = plt.cm.Set3(np.linspace(0, 1, 12))
            self.camera_colors[camera_id] = colors[camera_id % len(colors)]
        return self.camera_colors[camera_id]