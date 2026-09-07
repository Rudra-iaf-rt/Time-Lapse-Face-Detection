# face/face_embedder.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import numpy as np
import cv2
from typing import Optional, List, Tuple
import torchvision.transforms as transforms

class ArcFaceEmbedder:
    """
    ArcFace embedding extractor for face recognition.
    """
    
    def __init__(self, 
                 model_name: str = "ir_se50",
                 model_path: Optional[str] = None,
                 device: str = "cuda",
                 input_size: Tuple[int, int] = (112, 112)):
        """
        Initialize ArcFace embedder.
        
        Args:
            model_name: Model architecture name
            model_path: Path to pretrained weights
            device: 'cuda' or 'cpu'
            input_size: (width, height) of input face
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.input_size = input_size
        self.embedding_dim = 512
        
        # Initialize model
        self.model = self._build_model(model_name)
        
        # Load pretrained weights
        if model_path:
            self._load_weights(model_path)
        else:
            print("⚠️ No model path provided, using random weights for demo")
        
        self.model = self.model.to(self.device)
        self.model.eval()
        
        # Preprocessing transforms
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.5, 0.5, 0.5],
                std=[0.5, 0.5, 0.5]
            )
        ])
    
    def _build_model(self, model_name: str) -> nn.Module:
        """
        Build ArcFace model.
        
        Note: This is a simplified version. In practice, use the official 
        ArcFace implementation or insightface library.
        """
        try:
            # Use insightface for ArcFace
            import insightface
            from insightface.model_zoo import get_model
            
            # Download model if not available
            model = get_model('arcface_r100_v1')
            model.prepare(ctx_id=0 if self.device == "cuda" else -1)
            return model
            
        except ImportError:
            print("⚠️ insightface not installed, using simplified model")
            return self._build_simple_model()
    
    def _build_simple_model(self) -> nn.Module:
        """
        Build a simplified face embedding model.
        
        This is for testing only. Real ArcFace requires pretrained weights.
        """
        from torchvision.models import resnet50
        
        model = resnet50(pretrained=False)
        model.fc = nn.Linear(2048, self.embedding_dim)
        
        return model
    
    def _load_weights(self, model_path: str):
        """Load pretrained weights."""
        try:
            if hasattr(self.model, 'load_state_dict'):
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"✅ Loaded ArcFace weights from {model_path}")
        except Exception as e:
            print(f"⚠️ Could not load weights: {e}")
    
    def extract_embedding(self, face_image: np.ndarray) -> np.ndarray:
        """
        Extract face embedding.
        
        Args:
            face_image: Face image (BGR or RGB)
            
        Returns:
            512-D embedding vector (L2 normalized)
        """
        if face_image is None or face_image.size == 0:
            return np.zeros(self.embedding_dim, dtype=np.float32)
        
        # Convert BGR to RGB if needed
        if len(face_image.shape) == 3 and face_image.shape[2] == 3:
            # Check if it's BGR (OpenCV default)
            if isinstance(face_image, np.ndarray):
                rgb_face = cv2.cvtColor(face_image, cv2.COLOR_BGR2RGB)
            else:
                rgb_face = face_image
        else:
            rgb_face = face_image
        
        # Check if using insightface
        if hasattr(self.model, 'get_embedding'):
            # insightface expects RGB
            embedding = self.model.get_embedding(rgb_face)
            return embedding.astype(np.float32)
        
        # Use PyTorch model
        input_tensor = self.transform(rgb_face).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            embedding = self.model(input_tensor)
            embedding = F.normalize(embedding, p=2, dim=1)
        
        return embedding.cpu().numpy().squeeze().astype(np.float32)
    
    def batch_extract(self, face_images: List[np.ndarray]) -> List[np.ndarray]:
        """Batch extract face embeddings."""
        embeddings = []
        for face_img in face_images:
            emb = self.extract_embedding(face_img)
            embeddings.append(emb)
        return embeddings
    
    def compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between face embeddings."""
        if emb1.shape != emb2.shape:
            return 0.0
        return float(np.dot(emb1, emb2))