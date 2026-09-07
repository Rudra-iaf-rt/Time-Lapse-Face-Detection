# face/face_detector.py
import cv2
import numpy as np
from typing import List, Dict, Tuple, Optional
import torch

class FaceDetector:
    """
    Face detector using MTCNN or RetinaFace.
    """
    
    def __init__(self, 
                 method: str = "mtcnn",
                 device: str = "cuda",
                 min_face_size: int = 20,
                 confidence_threshold: float = 0.9):
        """
        Initialize face detector.
        
        Args:
            method: 'mtcnn' or 'retinaface'
            device: 'cuda' or 'cpu'
            min_face_size: Minimum face size to detect
            confidence_threshold: Detection confidence threshold
        """
        self.method = method
        self.device = device if torch.cuda.is_available() else "cpu"
        self.min_face_size = min_face_size
        self.confidence_threshold = confidence_threshold
        
        self._init_detector()
    
    def _init_detector(self):
        """Initialize the face detector."""
        if self.method == "mtcnn":
            try:
                from facenet_pytorch import MTCNN
                self.detector = MTCNN(
                    image_size=160,
                    margin=0,
                    min_face_size=self.min_face_size,
                    thresholds=[0.6, 0.7, 0.8],
                    factor=0.709,
                    post_process=True,
                    device=self.device
                )
                print("✅ MTCNN face detector initialized")
            except ImportError:
                print("⚠️ MTCNN not installed, falling back to OpenCV")
                self._init_opencv_detector()
                
        elif self.method == "retinaface":
            try:
                from retinaface import RetinaFace
                self.detector = RetinaFace
                print("✅ RetinaFace detector initialized")
            except ImportError:
                print("⚠️ RetinaFace not installed, falling back to OpenCV")
                self._init_opencv_detector()
        else:
            self._init_opencv_detector()
    
    def _init_opencv_detector(self):
        """Initialize OpenCV Haar cascade detector (fallback)."""
        cascade_path = cv2.data.haarcascades + 'haarcascade_frontalface_default.xml'
        self.detector = cv2.CascadeClassifier(cascade_path)
        print("✅ OpenCV Haar cascade detector initialized (fallback)")
    
    def detect_faces(self, image: np.ndarray) -> List[Dict]:
        """
        Detect faces in an image.
        
        Args:
            image: BGR image (numpy array)
            
        Returns:
            List of face detections with bbox, confidence, landmarks
        """
        if image is None or image.size == 0:
            return []
        
        # Convert BGR to RGB for face detectors
        rgb_image = cv2.cvtColor(image, cv2.COLOR_BGR2RGB)
        
        if self.method == "mtcnn":
            return self._detect_mtcnn(rgb_image)
        elif self.method == "retinaface":
            return self._detect_retinaface(rgb_image)
        else:
            return self._detect_opencv(image)
    
    def _detect_mtcnn(self, rgb_image: np.ndarray) -> List[Dict]:
        """Detect faces using MTCNN."""
        try:
            # MTCNN returns boxes, probs, landmarks
            boxes, probs, landmarks = self.detector.detect(
                rgb_image, landmarks=True
            )
            
            if boxes is None:
                return []
            
            detections = []
            for i, box in enumerate(boxes):
                if probs[i] >= self.confidence_threshold:
                    # Convert to integer coordinates
                    x1, y1, x2, y2 = map(int, box)
                    
                    # Extract landmarks if available
                    face_landmarks = None
                    if landmarks is not None and len(landmarks) > i:
                        # MTCNN returns landmarks as [x1,y1,x2,y2,...]
                        lm = landmarks[i]
                        if lm is not None:
                            face_landmarks = {
                                'left_eye': (int(lm[0]), int(lm[1])),
                                'right_eye': (int(lm[2]), int(lm[3])),
                                'nose': (int(lm[4]), int(lm[5])),
                                'left_mouth': (int(lm[6]), int(lm[7])),
                                'right_mouth': (int(lm[8]), int(lm[9]))
                            }
                    
                    detections.append({
                        'bbox': [x1, y1, x2, y2],
                        'confidence': float(probs[i]),
                        'landmarks': face_landmarks,
                        'area': (x2 - x1) * (y2 - y1)
                    })
            
            return detections
            
        except Exception as e:
            print(f"⚠️ MTCNN detection error: {e}")
            return []
    
    def _detect_retinaface(self, rgb_image: np.ndarray) -> List[Dict]:
        """Detect faces using RetinaFace."""
        try:
            import retinaface
            
            # RetinaFace expects RGB image
            faces = self.detector.detect_faces(rgb_image)
            
            detections = []
            for face_key, face_data in faces.items():
                confidence = face_data['score']
                if confidence >= self.confidence_threshold:
                    # Get bounding box
                    bbox = face_data['facial_area']
                    x1, y1, x2, y2 = bbox
                    
                    # Get landmarks
                    landmarks = face_data['landmarks']
                    face_landmarks = {
                        'left_eye': tuple(map(int, landmarks['left_eye'])),
                        'right_eye': tuple(map(int, landmarks['right_eye'])),
                        'nose': tuple(map(int, landmarks['nose'])),
                        'left_mouth': tuple(map(int, landmarks['mouth_left'])),
                        'right_mouth': tuple(map(int, landmarks['mouth_right']))
                    }
                    
                    detections.append({
                        'bbox': [int(x1), int(y1), int(x2), int(y2)],
                        'confidence': float(confidence),
                        'landmarks': face_landmarks,
                        'area': (x2 - x1) * (y2 - y1)
                    })
            
            return detections
            
        except Exception as e:
            print(f"⚠️ RetinaFace detection error: {e}")
            return []
    
    def _detect_opencv(self, image: np.ndarray) -> List[Dict]:
        """Detect faces using OpenCV Haar cascade."""
        gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
        
        faces = self.detector.detectMultiScale(
            gray,
            scaleFactor=1.1,
            minNeighbors=5,
            minSize=(self.min_face_size, self.min_face_size)
        )
        
        detections = []
        for (x, y, w, h) in faces:
            detections.append({
                'bbox': [int(x), int(y), int(x + w), int(y + h)],
                'confidence': 0.8,  # Haar doesn't provide confidence
                'landmarks': None,
                'area': w * h
            })
        
        return detections
    
    def get_best_face(self, image: np.ndarray) -> Optional[Dict]:
        """
        Get the best (largest, highest confidence) face detection.
        
        Returns:
            Best face detection or None
        """
        detections = self.detect_faces(image)
        
        if not detections:
            return None
        
        # Score faces by confidence and area
        for det in detections:
            det['score'] = det['confidence'] * (det['area'] / 10000)
        
        # Return highest scored face
        return max(detections, key=lambda x: x['score'])

    def get_faces_with_person(self, person_crop: np.ndarray, 
                             person_bbox: List[float]) -> List[Dict]:
        """
        Detect faces within a person crop and return relative positions.
        
        Args:
            person_crop: Person crop image
            person_bbox: Person bounding box [x1, y1, x2, y2]
            
        Returns:
            List of face detections with relative coordinates
        """
        faces = self.detect_faces(person_crop)
        
        # Convert face coordinates to original image coordinates
        for face in faces:
            x1, y1, x2, y2 = face['bbox']
            face['bbox_original'] = [
                person_bbox[0] + x1,
                person_bbox[1] + y1,
                person_bbox[0] + x2,
                person_bbox[1] + y2
            ]
        
        return faces