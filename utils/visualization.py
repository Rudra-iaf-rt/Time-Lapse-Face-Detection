# utils/visualization.py
import cv2
import numpy as np
from typing import Dict, List, Optional

def draw_reid_info(frame: np.ndarray, detection: Dict) -> np.ndarray:
    """Draw Re-ID information on frame."""
    if detection is None or detection.get('quality_skipped', True):
        return frame
        
    bbox = detection.get('bbox', [0, 0, 100, 200])
    x1, y1, x2, y2 = map(int, bbox)
    
    global_id = detection.get('global_id', 'UNKNOWN')
    quality = detection.get('reid_quality', {})
    quality_score = quality.get('overall', 0.0)
    
    # Color based on global ID
    color = _id_to_color(global_id)
    
    # Draw bounding box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color, 2)
    
    # Draw global ID
    label = f"ID: {global_id[-8:]}"
    if global_id != 'UNKNOWN':
        label += f" ({quality_score:.2f})"
    
    label_size = cv2.getTextSize(label, cv2.FONT_HERSHEY_SIMPLEX, 0.5, 1)[0]
    cv2.rectangle(frame, (x1, y1 - label_size[1] - 10),
                  (x1 + label_size[0], y1), color, -1)
    cv2.putText(frame, label, (x1, y1 - 5),
                cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 1)
    
    return frame

def _id_to_color(global_id: str) -> tuple:
    """Convert global ID to consistent color."""
    if global_id == 'UNKNOWN':
        return (128, 128, 128)  # Gray
    
    # Hash ID to RGB
    import hashlib
    hash_val = int(hashlib.md5(global_id.encode()).hexdigest()[:6], 16)
    r = (hash_val >> 16) & 0xFF
    g = (hash_val >> 8) & 0xFF
    b = hash_val & 0xFF
    
    return (b, g, r)  # OpenCV uses BGR

def draw_similarity_matrix(matrix: np.ndarray, labels: List[str],
                          frame_size: tuple = (500, 500)) -> np.ndarray:
    """Draw similarity matrix for visualization."""
    n = len(labels)
    if n == 0:
        return np.zeros(frame_size, dtype=np.uint8)
    
    img = np.ones((frame_size[1], frame_size[0], 3), dtype=np.uint8) * 255
    
    # Calculate cell size
    margin = 50
    cell_size = min((frame_size[0] - margin * 2) // n,
                    (frame_size[1] - margin * 2) // n)
    
    for i in range(n):
        for j in range(n):
            x = margin + j * cell_size
            y = margin + i * cell_size
            
            # Color based on similarity
            sim = matrix[i, j]
            intensity = int(sim * 255)
            color = (intensity, intensity, 255)  # Blue scale
            cv2.rectangle(img, (x, y), (x + cell_size, y + cell_size),
                         color, -1)
            cv2.rectangle(img, (x, y), (x + cell_size, y + cell_size),
                         (0, 0, 0), 1)
            
            # Show value
            if i != j:
                text = f"{sim:.2f}"
                cv2.putText(img, text, (x + 5, y + cell_size // 2 + 5),
                           cv2.FONT_HERSHEY_SIMPLEX, 0.3, (0, 0, 0), 1)
    
    return img