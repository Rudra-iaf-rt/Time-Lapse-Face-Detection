# face/face_aligner.py
import cv2
import numpy as np
from typing import Dict, Tuple, Optional
import math

class FaceAligner:
    """
    Face alignment using landmarks.
    """
    
    def __init__(self, output_size: Tuple[int, int] = (112, 112)):
        """
        Initialize face aligner.
        
        Args:
            output_size: (width, height) of aligned face
        """
        self.output_size = output_size
        
    def align_face(self, image: np.ndarray, 
                   landmarks: Dict) -> Optional[np.ndarray]:
        """
        Align face using eye landmarks.
        
        Args:
            image: Input image
            landmarks: Face landmarks dict with 'left_eye' and 'right_eye'
            
        Returns:
            Aligned face image
        """
        if landmarks is None or 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            return self.crop_face(image, landmarks)
        
        # Get eye coordinates
        left_eye = landmarks['left_eye']
        right_eye = landmarks['right_eye']
        
        # Calculate angle
        eye_center = ((left_eye[0] + right_eye[0]) // 2,
                      (left_eye[1] + right_eye[1]) // 2)
        
        dy = right_eye[1] - left_eye[1]
        dx = right_eye[0] - left_eye[0]
        angle = math.degrees(math.atan2(dy, dx))
        
        # Calculate desired eye distance (for scaling)
        desired_eye_distance = 0.3 * self.output_size[0]
        eye_distance = math.sqrt(dx**2 + dy**2)
        scale = desired_eye_distance / eye_distance if eye_distance > 0 else 1.0
        
        # Get rotation matrix
        rotation_matrix = cv2.getRotationMatrix2D(eye_center, angle, scale)
        
        # Apply rotation
        rotated = cv2.warpAffine(
            image,
            rotation_matrix,
            (image.shape[1], image.shape[0]),
            flags=cv2.INTER_CUBIC
        )
        
        # Calculate crop region
        crop_size = int(self.output_size[0] / 0.6)  # 60% of output size
        x = eye_center[0] - crop_size // 2
        y = eye_center[1] - crop_size // 2
        
        # Crop face
        cropped = rotated[y:y+crop_size, x:x+crop_size]
        
        # Resize to output size
        aligned = cv2.resize(cropped, self.output_size, interpolation=cv2.INTER_CUBIC)
        
        return aligned
    
    def crop_face(self, image: np.ndarray, 
                  landmarks: Optional[Dict] = None) -> np.ndarray:
        """
        Simple face cropping without alignment.
        
        Args:
            image: Input image
            landmarks: Optional landmarks for better cropping
            
        Returns:
            Cropped face image
        """
        if image is None or image.size == 0:
            return None
            
        h, w = image.shape[:2]
        
        # Use center crop
        size = min(h, w)
        x = (w - size) // 2
        y = (h - size) // 2
        
        cropped = image[y:y+size, x:x+size]
        
        # Resize to output size
        return cv2.resize(cropped, self.output_size, interpolation=cv2.INTER_CUBIC)
    
    def align_faces(self, image: np.ndarray, 
                    face_detections: list) -> list:
        """
        Align multiple faces.
        
        Args:
            image: Input image
            face_detections: List of face detections with landmarks
            
        Returns:
            List of aligned face images
        """
        aligned_faces = []
        
        for detection in face_detections:
            landmarks = detection.get('landmarks')
            
            # Extract face region
            bbox = detection['bbox']
            x1, y1, x2, y2 = bbox
            
            # Add margin
            margin = int((x2 - x1) * 0.2)
            x1 = max(0, x1 - margin)
            y1 = max(0, y1 - margin)
            x2 = min(image.shape[1], x2 + margin)
            y2 = min(image.shape[0], y2 + margin)
            
            face_crop = image[y1:y2, x1:x2]
            
            if face_crop.size == 0:
                continue
            
            # Align face
            if landmarks:
                # Adjust landmarks relative to crop
                adjusted_landmarks = {}
                for key, (lx, ly) in landmarks.items():
                    adjusted_landmarks[key] = (lx - x1, ly - y1)
                
                aligned = self.align_face(face_crop, adjusted_landmarks)
            else:
                aligned = self.crop_face(face_crop)
            
            if aligned is not None:
                aligned_faces.append({
                    'aligned_face': aligned,
                    'bbox': bbox,
                    'confidence': detection.get('confidence', 0.0)
                })
        
        return aligned_faces