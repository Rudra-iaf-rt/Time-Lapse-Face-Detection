# topology/topology_visualizer.py
import networkx as nx
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, Optional
import plotly.graph_objects as go
from plotly.subplots import make_subplots

class TopologyVisualizer:
    """Visualize camera topology graph."""
    
    def __init__(self, camera_graph):
        self.camera_graph = camera_graph
    
    def visualize_matplotlib(self, save_path: Optional[str] = None,
                            figsize: tuple = (12, 8)):
        """Visualize camera topology using matplotlib."""
        fig, ax = plt.subplots(figsize=figsize)
        
        G = self.camera_graph.graph
        
        # Get positions (use spring layout if no positions available)
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Draw nodes
        nx.draw_networkx_nodes(G, pos, node_size=1000, node_color='lightblue',
                              edgecolors='black', linewidths=2, ax=ax)
        
        # Draw labels
        nx.draw_networkx_labels(G, pos, font_size=12, font_weight='bold', ax=ax)
        
        # Draw edges with thickness based on probability
        for (from_cam, to_cam), transition in self.camera_graph.transitions.items():
            if from_cam in pos and to_cam in pos:
                prob = transition.transition_probability
                width = 1 + 4 * prob  # Thicker edge = higher probability
                alpha = 0.3 + 0.7 * prob
                
                nx.draw_networkx_edges(
                    G, pos, 
                    edgelist=[(from_cam, to_cam)],
                    width=width, 
                    alpha=alpha,
                    edge_color='blue',
                    arrows=True,
                    arrowsize=20,
                    ax=ax
                )
        
        # Add edge labels (travel times)
        edge_labels = {}
        for (from_cam, to_cam), transition in self.camera_graph.transitions.items():
            if from_cam in pos and to_cam in pos:
                label = f"{transition.avg_travel_time:.1f}s\n({transition.transition_probability:.2f})"
                edge_labels[(from_cam, to_cam)] = label
        
        nx.draw_networkx_edge_labels(G, pos, edge_labels, font_size=8, ax=ax)
        
        ax.set_title("Camera Topology Graph", fontsize=16, fontweight='bold')
        ax.axis('off')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Topology saved to {save_path}")
        
        plt.show()
    
    def visualize_plotly(self, save_path: Optional[str] = None):
        """Visualize camera topology using plotly (interactive)."""
        G = self.camera_graph.graph
        pos = nx.spring_layout(G, k=0.5, iterations=50)
        
        # Create edge traces
        edge_traces = []
        
        for (from_cam, to_cam), transition in self.camera_graph.transitions.items():
            if from_cam in pos and to_cam in pos:
                x0, y0 = pos[from_cam]
                x1, y1 = pos[to_cam]
                
                prob = transition.transition_probability
                width = 1 + 4 * prob
                
                edge_trace = go.Scatter(
                    x=[x0, x1, None],
                    y=[y0, y1, None],
                    mode='lines',
                    line=dict(
                        width=width,
                        color=f'rgba(0, 0, 255, {0.3 + 0.7 * prob})'
                    ),
                    hoverinfo='text',
                    text=f"{from_cam} → {to_cam}<br>"
                         f"Probability: {prob:.3f}<br>"
                         f"Travel time: {transition.avg_travel_time:.1f}s<br>"
                         f"Range: {transition.min_travel_time:.1f}-{transition.max_travel_time:.1f}s",
                    showlegend=False
                )
                edge_traces.append(edge_trace)
        
        # Create node trace
        node_x = []
        node_y = []
        node_text = []
        node_colors = []
        
        for camera_id, position in pos.items():
            node_x.append(position[0])
            node_y.append(position[1])
            
            # Get camera stats
            outgoing = len(self.camera_graph.get_possible_destinations(camera_id))
            incoming = len(self.camera_graph.get_possible_sources(camera_id))
            
            node_text.append(
                f"Camera {camera_id}<br>"
                f"Outgoing: {outgoing}<br>"
                f"Incoming: {incoming}"
            )
            
            # Color based on degree
            node_colors.append('lightblue')
        
        node_trace = go.Scatter(
            x=node_x,
            y=node_y,
            mode='markers+text',
            marker=dict(
                size=30,
                color=node_colors,
                line=dict(color='black', width=2)
            ),
            text=[f"Cam {cam}" for cam in pos.keys()],
            textposition="middle center",
            hoverinfo='text',
            hovertext=node_text,
            showlegend=False
        )
        
        # Create figure
        fig = go.Figure(
            data=edge_traces + [node_trace],
            layout=go.Layout(
                title=dict(
                    text="Camera Topology Graph",
                    font=dict(size=20)
                ),
                showlegend=False,
                hovermode='closest',
                xaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                yaxis=dict(showgrid=False, zeroline=False, showticklabels=False),
                width=800,
                height=600
            )
        )
        
        if save_path:
            fig.write_html(save_path)
            print(f"✅ Interactive topology saved to {save_path}")
        
        fig.show()
    
    def visualize_transition_matrix(self, save_path: Optional[str] = None):
        """Visualize transition probability matrix as heatmap."""
        cameras = sorted(self.camera_graph.graph.nodes())
        n = len(cameras)
        matrix = np.zeros((n, n))
        
        for i, from_cam in enumerate(cameras):
            for j, to_cam in enumerate(cameras):
                if i != j:
                    matrix[i, j] = self.camera_graph.get_transition_probability(
                        from_cam, to_cam
                    )
        
        fig, ax = plt.subplots(figsize=(10, 8))
        
        im = ax.imshow(matrix, cmap='YlOrRd', aspect='auto', vmin=0, vmax=1)
        
        # Add colorbar
        cbar = plt.colorbar(im, ax=ax)
        cbar.set_label('Transition Probability', fontsize=12)
        
        # Add labels
        ax.set_xticks(np.arange(n))
        ax.set_yticks(np.arange(n))
        ax.set_xticklabels([f'Cam {c}' for c in cameras])
        ax.set_yticklabels([f'Cam {c}' for c in cameras])
        
        # Rotate x labels
        plt.setp(ax.get_xticklabels(), rotation=45, ha="right", rotation_mode="anchor")
        
        # Add text annotations
        for i in range(n):
            for j in range(n):
                if i != j and matrix[i, j] > 0.01:
                    text = ax.text(j, i, f'{matrix[i, j]:.2f}',
                                 ha="center", va="center", 
                                 color="black" if matrix[i, j] < 0.5 else "white",
                                 fontsize=8)
        
        ax.set_title('Camera Transition Probability Matrix', fontsize=16, fontweight='bold')
        ax.set_xlabel('Destination Camera', fontsize=12)
        ax.set_ylabel('Source Camera', fontsize=12)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"✅ Transition matrix saved to {save_path}")
        
        plt.show()