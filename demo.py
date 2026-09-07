# demo.py
import cv2
import numpy as np
import os
import sys
from datetime import datetime

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from reid.osnet_model import OSNetReIDExtractor
from reid.quality_estimator import QualityEstimator
from reid.reid_gallery import ReIDGallery

def create_sample_crops():
    """Create sample person crops for demo."""
    print("📸 Creating sample person crops...")
    
    # Create a directory for sample crops
    os.makedirs("tests/test_data/sample_crops", exist_ok=True)
    
    # Generate different person crops
    crops = []
    person_ids = []
    
    # Person 1 - 5 variations (same person, different poses)
    for i in range(5):
        crop = np.random.randint(0, 255, (256, 128, 3), dtype=np.uint8)
        # Add some variation
        crop = cv2.addWeighted(crop, 0.7, 
                              np.random.randint(0, 50, crop.shape, dtype=np.uint8), 
                              0.3, 0)
        crops.append(crop)
        person_ids.append("PERSON_001")
    
    # Person 2 - 5 variations (different person)
    for i in range(5):
        crop = np.random.randint(0, 200, (256, 128, 3), dtype=np.uint8)
        crop = cv2.addWeighted(crop, 0.7, 
                              np.random.randint(50, 100, crop.shape, dtype=np.uint8), 
                              0.3, 0)
        crops.append(crop)
        person_ids.append("PERSON_002")
    
    # Save crops for visualization
    for i, crop in enumerate(crops):
        cv2.imwrite(f"tests/test_data/sample_crops/crop_{i:03d}.jpg", crop)
    
    print(f"✅ Created {len(crops)} sample crops")
    return crops, person_ids

def run_simple_demo():
    """Run a simple Re-ID demo."""
    print("\n" + "=" * 60)
    print("🎯 Simple Re-ID Demo")
    print("=" * 60)
    
    # 1. Initialize components
    print("\n1️⃣ Initializing components...")
    extractor = OSNetReIDExtractor()
    quality_estimator = QualityEstimator()
    gallery = ReIDGallery(db_path="tests/test_data/demo_reid.db")
    
    # 2. Create sample data
    crops, person_ids = create_sample_crops()
    
    # 3. Extract embeddings and add to gallery
    print("\n2️⃣ Extracting embeddings...")
    embeddings = []
    
    for i, crop in enumerate(crops):
        # Estimate quality
        quality = quality_estimator.estimate_quality(crop)
        
        # Extract embedding
        embedding = extractor.extract_embedding(crop)
        embeddings.append(embedding)
        
        # Add to gallery with simulated track ID
        track_id = f"DEMO_{i:03d}"
        global_id = gallery.add_observation(
            camera_id=i // 5,  # Person 1: camera 0, Person 2: camera 1
            track_id=track_id,
            embedding=embedding,
            quality=quality['overall'],
            timestamp=datetime.now()
        )
        
        print(f"   - Crop {i:03d}: Quality={quality['overall']:.3f}, Global ID={global_id}")
    
    # 4. Compute similarity matrix
    print("\n3️⃣ Computing similarity matrix...")
    n = len(embeddings)
    similarity_matrix = np.zeros((n, n))
    
    for i in range(n):
        for j in range(n):
            similarity_matrix[i, j] = extractor.compute_similarity(embeddings[i], embeddings[j])
    
    # 5. Show results
    print("\n4️⃣ Results:")
    print("-" * 60)
    
    # Show within-person similarities (same person)
    within_person = []
    for i in range(5):
        for j in range(i+1, 5):
            sim = similarity_matrix[i, j]
            within_person.append(sim)
    
    # Show between-person similarities (different people)
    between_person = []
    for i in range(5):
        for j in range(5, 10):
            sim = similarity_matrix[i, j]
            between_person.append(sim)
    
    print(f"   Within-person similarity (mean): {np.mean(within_person):.3f}")
    print(f"   Within-person similarity (std):  {np.std(within_person):.3f}")
    print(f"   Between-person similarity (mean): {np.mean(between_person):.3f}")
    print(f"   Between-person similarity (std):  {np.std(between_person):.3f}")
    
    # 6. Gallery statistics
    print("\n5️⃣ Gallery Statistics:")
    stats = gallery.get_statistics()
    print(f"   Total identities: {stats['total_identities']}")
    print(f"   Total profiles: {stats['total_profiles']}")
    print(f"   Camera profiles: {stats['camera_profiles']}")
    
    print("\n" + "=" * 60)
    print("✅ Demo completed successfully!")

def main():
    # Check if we're in the right directory
    if not os.path.exists("tests"):
        os.makedirs("tests/test_data", exist_ok=True)
        os.makedirs("tests/test_results", exist_ok=True)
    
    # Run demo
    run_simple_demo()

if __name__ == "__main__":
    main()