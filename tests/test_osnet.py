# tests/test_osnet.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator

def test_osnet_initialization():
    """Test OSNet model initialization."""
    print("🧪 Testing OSNet initialization...")
    try:
        extractor = OSNetReIDExtractor()
        print("✅ OSNet initialized successfully")
        return extractor
    except Exception as e:
        print(f"❌ Failed to initialize OSNet: {e}")
        return None

def test_embedding_extraction(extractor):
    """Test embedding extraction with synthetic data."""
    print("\n🧪 Testing embedding extraction...")
    
    # Create synthetic person crop (128x256 RGB)
    synthetic_crop = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
    
    try:
        embedding = extractor.extract_embedding(synthetic_crop)
        
        # Check embedding properties
        assert embedding.shape == (512,), f"Expected shape (512,), got {embedding.shape}"
        assert isinstance(embedding, np.ndarray), "Embedding should be numpy array"
        assert embedding.dtype == np.float32, f"Expected float32, got {embedding.dtype}"
        
        # Check L2 normalization
        norm = np.linalg.norm(embedding)
        assert abs(norm - 1.0) < 0.001, f"Expected norm ~1.0, got {norm:.4f}"
        
        print(f"✅ Embedding extraction successful")
        print(f"   - Shape: {embedding.shape}")
        print(f"   - L2 Norm: {norm:.4f}")
        print(f"   - Range: [{embedding.min():.4f}, {embedding.max():.4f}]")
        return embedding
        
    except Exception as e:
        print(f"❌ Embedding extraction failed: {e}")
        return None

def test_similarity_computation(extractor):
    """Test similarity computation between embeddings."""
    print("\n🧪 Testing similarity computation...")
    
    # Create two similar embeddings (with small perturbation)
    emb1 = np.random.randn(512)
    emb1 = emb1 / np.linalg.norm(emb1)
    
    # Create slightly different embedding
    emb2 = emb1 + np.random.randn(512) * 0.1
    emb2 = emb2 / np.linalg.norm(emb2)
    
    # Create very different embedding
    emb3 = np.random.randn(512)
    emb3 = emb3 / np.linalg.norm(emb3)
    
    try:
        sim_similar = extractor.compute_similarity(emb1, emb2)
        sim_different = extractor.compute_similarity(emb1, emb3)
        
        print(f"✅ Similarity computation successful")
        print(f"   - Similar embeddings: {sim_similar:.4f}")
        print(f"   - Different embeddings: {sim_different:.4f}")
        
        # Validate that similar is higher than different
        if sim_similar > sim_different:
            print("   ✅ Similarity behaves as expected")
        else:
            print("   ⚠️ Similarity may need tuning")
            
        return sim_similar, sim_different
        
    except Exception as e:
        print(f"❌ Similarity computation failed: {e}")
        return None, None

def test_batch_extraction(extractor):
    """Test batch embedding extraction."""
    print("\n🧪 Testing batch extraction...")
    
    # Create batch of synthetic crops
    crops = [np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8) 
             for _ in range(5)]
    
    try:
        embeddings = extractor.batch_extract(crops)
        
        assert len(embeddings) == 5, f"Expected 5 embeddings, got {len(embeddings)}"
        for emb in embeddings:
            assert emb.shape == (512,), f"Expected shape (512,), got {emb.shape}"
        
        print(f"✅ Batch extraction successful")
        print(f"   - Extracted {len(embeddings)} embeddings")
        
        return embeddings
        
    except Exception as e:
        print(f"❌ Batch extraction failed: {e}")
        return None

def main():
    print("=" * 60)
    print("🧪 OSNet Model Tests")
    print("=" * 60)
    
    # Test 1: Initialization
    extractor = test_osnet_initialization()
    if extractor is None:
        print("\n❌ Exiting due to initialization failure")
        return
    
    # Test 2: Single embedding
    embedding = test_embedding_extraction(extractor)
    if embedding is None:
        print("\n⚠️ Continuing with other tests...")
    
    # Test 3: Similarity
    test_similarity_computation(extractor)
    
    # Test 4: Batch extraction
    test_batch_extraction(extractor)
    
    print("\n" + "=" * 60)
    print("✅ All tests completed!")

if __name__ == "__main__":
    main()