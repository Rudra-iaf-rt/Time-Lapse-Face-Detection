# face/face_quality.py
import cv2
import numpy as np
from typing import Dict, Tuple
import math

class FaceQualityEstimator:
    """
    Face quality estimation for better matching.
    """
    
    def __init__(self):
        self.weights = {
            'resolution': 0.20,
            'blur': 0.25,
            'contrast': 0.15,
            'brightness': 0.10,
            'pose': 0.20,
            'occlusion': 0.10
        }
    
    def estimate_quality(self, face_image: np.ndarray,
                        landmarks: Dict = None) -> Dict:
        """
        Estimate quality of a face image.
        
        Args:
            face_image: Face image
            landmarks: Face landmarks for pose estimation
            
        Returns:
            Quality metrics dictionary
        """
        if face_image is None or face_image.size == 0:
            return {'overall': 0.0}
        
        # Convert to grayscale
        if len(face_image.shape) == 3:
            gray = cv2.cvtColor(face_image, cv2.COLOR_BGR2GRAY)
        else:
            gray = face_image
        
        h, w = gray.shape
        
        # 1. Resolution quality
        resolution_score = min(1.0, (h * w) / (112 * 112))
        
        # 2. Blur quality (Laplacian variance)
        laplacian_var = cv2.Laplacian(gray, cv2.CV_64F).var()
        blur_score = min(1.0, laplacian_var / 3000)
        
        # 3. Contrast quality
        contrast = np.std(gray)
        contrast_score = min(1.0, contrast / 128)
        
        # 4. Brightness quality
        brightness = np.mean(gray)
        brightness_score = 1.0 - abs(brightness - 128) / 128
        
        # 5. Pose quality (if landmarks available)
        pose_score = 1.0
        if landmarks:
            pose_score = self._estimate_pose_quality(landmarks)
        
        # 6. Occlusion quality
        occlusion_score = self._estimate_occlusion(gray)
        
        # Combine scores
        overall = (
            resolution_score * self.weights['resolution'] +
            blur_score * self.weights['blur'] +
            contrast_score * self.weights['contrast'] +
            brightness_score * self.weights['brightness'] +
            pose_score * self.weights['pose'] +
            occlusion_score * self.weights['occlusion']
        )
        
        return {
            'overall': float(overall),
            'resolution': float(resolution_score),
            'blur': float(blur_score),
            'contrast': float(contrast_score),
            'brightness': float(brightness_score),
            'pose': float(pose_score),
            'occlusion': float(occlusion_score),
            'resolution_actual': (h, w)
        }
    
    def _estimate_pose_quality(self, landmarks: Dict) -> float:
        """
        Estimate head pose quality from landmarks.
        """
        if not landmarks or 'left_eye' not in landmarks or 'right_eye' not in landmarks:
            return 0.5
        
        left_eye = landmarks['left_eye']
        right_eye = landmarks['right_eye']
        nose = landmarks.get('nose')
        left_mouth = landmarks.get('left_mouth')
        right_mouth = landmarks.get('right_mouth')
        
        # Check eye symmetry
        eye_distance = math.sqrt(
            (right_eye[0] - left_eye[0])**2 + 
            (right_eye[1] - left_eye[1])**2
        )
        
        if eye_distance == 0:
            return 0.5
        
        # Check if eyes are horizontal
        eye_angle = abs(math.degrees(math.atan2(
            right_eye[1] - left_eye[1],
            right_eye[0] - left_eye[0]
        )))
        
        # Good if eye angle is close to 0
        angle_score = max(0, 1 - eye_angle / 45)
        
        # Check nose position relative to eyes
        if nose:
            nose_center_x = (left_eye[0] + right_eye[0]) / 2
            nose_offset = abs(nose[0] - nose_center_x) / eye_distance
            nose_score = max(0, 1 - nose_offset)
        else:
            nose_score = 0.5
        
        # Combine scores
        pose_score = (angle_score * 0.6 + nose_score * 0.4)
        
        return min(1.0, pose_score)
    
    def _estimate_occlusion(self, gray_image: np.ndarray) -> float:
        """
        Estimate occlusion quality using edge detection.
        """
        # Detect edges
        edges = cv2.Canny(gray_image, 100, 200)
        
        # Calculate edge density
        edge_density = np.sum(edges > 0) / edges.size
        
        # High edge density might indicate texture (good)
        # Very high density might indicate noise (bad)
        if edge_density < 0.05:
            return 0.3  # Too smooth - possible occlusion
        elif edge_density > 0.8:
            return 0.4  # Too noisy - possible occlusion
        else:
            return min(1.0, edge_density * 1.5)
    
    def get_best_face(self, face_images: list) -> Tuple[int, float]:
        """
        Get the best quality face from a list.
        
        Returns:
            (index, quality_score)
        """
        if not face_images:
            return -1, 0.0
        
        scores = []
        for face_img in face_images:
            quality = self.estimate_quality(face_img)
            scores.append(quality['overall'])
        
        best_idx = np.argmax(scores)
        return best_idx, scores[best_idx]