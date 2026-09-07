# tests/test_face.py
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

import cv2
import numpy as np
from face.face_detector import FaceDetector
from face.face_aligner import FaceAligner
from face.face_embedder import ArcFaceEmbedder
from face.face_quality import FaceQualityEstimator
from face.face_gallery import FaceGallery

def test_face_detection():
    """Test face detection."""
    print("🧪 Testing face detection...")
    
    detector = FaceDetector(method='mtcnn')
    
    # Create synthetic image with faces
    img = np.ones((480, 640, 3), dtype=np.uint8) * 128
    
    # Draw a face
    cv2.rectangle(img, (200, 100), (300, 250), (200, 150, 100), -1)  # Face
    cv2.circle(img, (235, 150), 10, (0, 0, 0), -1)  # Left eye
    cv2.circle(img, (265, 150), 10, (0, 0, 0), -1)  # Right eye
    cv2.circle(img, (250, 180), 8, (0, 0, 0), -1)   # Nose
    
    faces = detector.detect_faces(img)
    print(f"   Detected {len(faces)} faces")
    
    for i, face in enumerate(faces):
        print(f"   Face {i+1}: bbox={face['bbox']}, confidence={face['confidence']:.3f}")
    
    return faces

def test_face_alignment():
    """Test face alignment."""
    print("\n🧪 Testing face alignment...")
    
    aligner = FaceAligner(output_size=(112, 112))
    
    # Create synthetic face
    face_img = np.random.randint(0, 255, (150, 120, 3), dtype=np.uint8)
    landmarks = {
        'left_eye': (40, 50),
        'right_eye': (80, 50),
        'nose': (60, 70)
    }
    
    aligned = aligner.align_face(face_img, landmarks)
    
    if aligned is not None:
        print(f"   Aligned face shape: {aligned.shape}")
        print(f"   ✅ Face alignment successful")
    else:
        print("   ❌ Face alignment failed")
    
    return aligned

def test_face_quality():
    """Test face quality estimation."""
    print("\n🧪 Testing face quality estimation...")
    
    estimator = FaceQualityEstimator()
    
    # Create different quality faces
    high_quality = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
    low_quality = np.random.randint(0, 255, (32, 32, 3), dtype=np.uint8)
    blurry = cv2.GaussianBlur(high_quality, (15, 15), 10)
    
    for name, img in [('High', high_quality), ('Low', low_quality), ('Blurry', blurry)]:
        quality = estimator.estimate_quality(img)
        print(f"   {name} quality: {quality['overall']:.3f}")
    
    return

def test_face_embedder():
    """Test face embedder."""
    print("\n🧪 Testing face embedder...")
    
    embedder = ArcFaceEmbedder()
    
    # Create synthetic face
    face_img = np.random.randint(0, 255, (112, 112, 3), dtype=np.uint8)
    
    embedding = embedder.extract_embedding(face_img)
    
    if embedding is not None:
        print(f"   Embedding shape: {embedding.shape}")
        print(f"   Embedding norm: {np.linalg.norm(embedding):.4f}")
        print(f"   ✅ Face embedding extracted")
    else:
        print("   ❌ Face embedding failed")
    
    return embedding

def test_face_gallery():
    """Test face gallery."""
    print("\n🧪 Testing face gallery...")
    
    gallery = FaceGallery("tests/test_data/face_test.db")
    
    # Create embeddings
    emb1 = np.random.randn(512)
    emb1 = emb1 / np.linalg.norm(emb1)
    
    emb2 = np.random.randn(512)
    emb2 = emb2 / np.linalg.norm(emb2)
    
    import datetime
    
    # Add faces
    gid1 = "TEST_001"
    gallery.add_face(gid1, emb1, 0.8, [0,0,100,100], 0, "T001", datetime.datetime.now())
    gallery.add_face(gid1, emb1, 0.7, [0,0,100,100], 1, "T002", datetime.datetime.now())
    
    gid2 = "TEST_002"
    gallery.add_face(gid2, emb2, 0.75, [0,0,100,100], 0, "T003", datetime.datetime.now())
    
    # Test matching
    matches = gallery.match_face(emb1, threshold=0.5)
    print(f"   Matches for emb1: {len(matches)}")
    for match in matches[:2]:
        print(f"   - {match['global_id']}: similarity={match['similarity']:.3f}")
    
    # Get statistics
    stats = gallery.get_gallery_statistics()
    print(f"   Gallery stats: {stats}")
    
    return gallery

def main():
    print("=" * 60)
    print("🧪 Phase 2 - Face Intelligence Tests")
    print("=" * 60)
    
    # Ensure test directory exists
    os.makedirs("tests/test_data", exist_ok=True)
    
    # Run tests
    test_face_detection()
    test_face_alignment()
    test_face_quality()
    test_face_embedder()
    test_face_gallery()
    
    print("\n" + "=" * 60)
    print("✅ All Phase 2 tests completed!")

if __name__ == "__main__":
    main()