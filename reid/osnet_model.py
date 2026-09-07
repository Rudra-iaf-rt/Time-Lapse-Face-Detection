# reid/osnet_model.py
import torch
import torch.nn as nn
import torch.nn.functional as F
import torchvision.transforms as transforms
import numpy as np
import cv2
from typing import Optional, List, Tuple
import warnings

class OSNet(nn.Module):
    """
    OSNet implementation for person re-identification.
    Simplified version - can be replaced with pretrained weights.
    """
    
    def __init__(self, num_features: int = 512, num_classes: int = 1000):
        super(OSNet, self).__init__()
        
        # Simplified backbone - use ResNet or MobileNet
        # In practice, load pretrained OSNet from torchreid or fastreid
        from torchvision.models import resnet50
        
        self.backbone = resnet50(pretrained=True)
        # Remove the final classification layer
        self.backbone.fc = nn.Identity()
        
        # Add Re-ID specific layers
        self.global_pool = nn.AdaptiveAvgPool2d((1, 1))
        self.fc = nn.Linear(2048, num_features)
        self.bn = nn.BatchNorm1d(num_features)
        
        # Initialize weights
        nn.init.kaiming_normal_(self.fc.weight, mode='fan_out', nonlinearity='relu')
        nn.init.constant_(self.bn.weight, 1)
        nn.init.constant_(self.bn.bias, 0)
        
    def forward(self, x):
        # Extract features
        x = self.backbone(x)
        x = self.global_pool(x)
        x = x.view(x.size(0), -1)
        x = self.fc(x)
        x = self.bn(x)
        return x

class OSNetReIDExtractor:
    """OSNet-based Re-ID feature extractor."""
    
    def __init__(self, 
                 model_path: Optional[str] = None,
                 device: str = "cuda",
                 input_size: tuple = (256, 128)):
        """
        Initialize OSNet Re-ID extractor.
        
        Args:
            model_path: Path to pretrained weights
            device: 'cuda' or 'cpu'
            input_size: (height, width) for model input
        """
        self.device = torch.device(device if torch.cuda.is_available() else "cpu")
        self.input_size = input_size
        
        # Initialize model
        self.model = OSNet(num_features=512)
        self.model = self.model.to(self.device)
        
        # Load pretrained weights if available
        if model_path:
            try:
                state_dict = torch.load(model_path, map_location=self.device)
                self.model.load_state_dict(state_dict)
                print(f"✅ Loaded OSNet weights from {model_path}")
            except Exception as e:
                print(f"⚠️ Could not load weights: {e}")
                print("Using random initialization - this is for demo only")
        
        self.model.eval()
        
        # Preprocessing transforms
        self.transform = transforms.Compose([
            transforms.ToPILImage(),
            transforms.Resize(input_size),
            transforms.ToTensor(),
            transforms.Normalize(
                mean=[0.485, 0.456, 0.406],
                std=[0.229, 0.224, 0.225]
            )
        ])
        
    def extract_embedding(self, crop: np.ndarray) -> np.ndarray:
        """
        Extract Re-ID embedding from person crop.
        
        Args:
            crop: BGR image (numpy array)
            
        Returns:
            L2-normalized embedding vector (512-D)
        """
        if crop is None or crop.size == 0:
            return np.zeros(512, dtype=np.float32)
            
        # Ensure RGB
        if len(crop.shape) == 3 and crop.shape[2] == 3:
            rgb_crop = cv2.cvtColor(crop, cv2.COLOR_BGR2RGB)
        else:
            rgb_crop = crop
            
        # Apply transforms
        input_tensor = self.transform(rgb_crop).unsqueeze(0).to(self.device)
        
        # Extract embedding
        with torch.no_grad():
            embedding = self.model(input_tensor)
            embedding = F.normalize(embedding, p=2, dim=1)
            
        return embedding.cpu().numpy().squeeze().astype(np.float32)
    
    def batch_extract(self, crops: List[np.ndarray]) -> List[np.ndarray]:
        """Batch extract embeddings from multiple crops."""
        embeddings = []
        for crop in crops:
            emb = self.extract_embedding(crop)
            embeddings.append(emb)
        return embeddings
    
    def compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity between two embeddings."""
        if emb1.shape != emb2.shape:
            return 0.0
        return float(np.dot(emb1, emb2))
    
    def compute_similarity_matrix(self, emb_list1: List[np.ndarray],
                                  emb_list2: List[np.ndarray]) -> np.ndarray:
        """Compute similarity matrix between two lists of embeddings."""
        matrix = np.zeros((len(emb_list1), len(emb_list2)))
        for i, emb1 in enumerate(emb_list1):
            for j, emb2 in enumerate(emb_list2):
                matrix[i, j] = self.compute_similarity(emb1, emb2)
        return matrix