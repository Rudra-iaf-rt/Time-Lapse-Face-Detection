# face/face_gallery.py
import numpy as np
import sqlite3
from typing import Dict, List, Optional, Tuple
from datetime import datetime
import json

class FaceGallery:
    """
    Face-specific gallery for storing and matching face embeddings.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize face-specific tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Face profiles table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                face_embedding BLOB,
                face_quality REAL,
                face_bbox TEXT,  # JSON string of [x1, y1, x2, y2]
                timestamp DATETIME,
                camera_id INTEGER,
                track_id TEXT,
                metadata TEXT
            )
        ''')
        
        # Face matches table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                matched_global_id TEXT,
                similarity REAL,
                quality_score REAL,
                matched_at DATETIME,
                metadata TEXT
            )
        ''')
        
        # Face statistics table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS face_statistics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                total_faces INTEGER,
                avg_quality REAL,
                last_seen DATETIME,
                best_face_quality REAL,
                best_face_timestamp DATETIME
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def add_face(self, global_id: str, face_embedding: np.ndarray,
                 quality: float, bbox: List[float],
                 camera_id: int, track_id: str,
                 timestamp: datetime,
                 metadata: Optional[Dict] = None) -> bool:
        """
        Add a face observation to gallery.
        """
        try:
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            
            # Store face profile
            emb_bytes = face_embedding.astype(np.float32).tobytes()
            bbox_json = json.dumps(bbox)
            metadata_json = json.dumps(metadata) if metadata else '{}'
            
            cursor.execute('''
                INSERT INTO face_profiles
                (global_id, face_embedding, face_quality, face_bbox,
                 timestamp, camera_id, track_id, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (global_id, emb_bytes, quality, bbox_json,
                  timestamp, camera_id, track_id, metadata_json))
            
            # Update face statistics
            self._update_statistics(global_id, quality, timestamp)
            
            conn.commit()
            conn.close()
            
            return True
            
        except Exception as e:
            print(f"⚠️ Failed to add face: {e}")
            return False
    
    def _update_statistics(self, global_id: str, quality: float,
                          timestamp: datetime):
        """Update face statistics for a global ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Check if exists
        cursor.execute('''
            SELECT id, total_faces, best_face_quality
            FROM face_statistics
            WHERE global_id = ?
        ''', (global_id,))
        
        result = cursor.fetchone()
        
        if result:
            # Update existing
            stat_id, total_faces, best_quality = result
            
            new_total = total_faces + 1
            new_avg_quality = (best_quality * total_faces + quality) / new_total
            new_best_quality = max(best_quality, quality)
            
            cursor.execute('''
                UPDATE face_statistics
                SET total_faces = ?,
                    avg_quality = ?,
                    last_seen = ?,
                    best_face_quality = ?,
                    best_face_timestamp = ?
                WHERE id = ?
            ''', (new_total, new_avg_quality, timestamp,
                  new_best_quality, timestamp if quality > best_quality else None,
                  stat_id))
        else:
            # Insert new
            cursor.execute('''
                INSERT INTO face_statistics
                (global_id, total_faces, avg_quality, last_seen,
                 best_face_quality, best_face_timestamp)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (global_id, 1, quality, timestamp, quality, timestamp))
        
        conn.commit()
        conn.close()
    
    def match_face(self, face_embedding: np.ndarray,
                   threshold: float = 0.6,
                   max_results: int = 10) -> List[Dict]:
        """
        Match a face embedding against the gallery.
        
        Returns:
            List of matches with global_id, similarity, quality
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get all face embeddings with their global IDs
        cursor.execute('''
            SELECT DISTINCT global_id, face_embedding, face_quality
            FROM face_profiles
            ORDER BY timestamp DESC
        ''')
        
        results = []
        for global_id, emb_bytes, quality in cursor.fetchall():
            if global_id is None:
                continue
                
            gallery_emb = np.frombuffer(emb_bytes, dtype=np.float32)
            
            # Compute similarity
            similarity = np.dot(face_embedding, gallery_emb)
            
            # Apply quality weighting
            weighted_similarity = similarity * (0.7 + 0.3 * quality)
            
            if weighted_similarity > threshold:
                results.append({
                    'global_id': global_id,
                    'similarity': float(similarity),
                    'weighted_similarity': float(weighted_similarity),
                    'quality': float(quality)
                })
        
        conn.close()
        
        # Sort by weighted similarity
        results.sort(key=lambda x: x['weighted_similarity'], reverse=True)
        
        return results[:max_results]
    
    def get_best_face_for_id(self, global_id: str) -> Optional[Dict]:
        """Get the best quality face for a global ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT face_embedding, face_quality, face_bbox, timestamp
            FROM face_profiles
            WHERE global_id = ?
            ORDER BY face_quality DESC
            LIMIT 1
        ''', (global_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            emb_bytes, quality, bbox_json, timestamp = result
            return {
                'embedding': np.frombuffer(emb_bytes, dtype=np.float32),
                'quality': float(quality),
                'bbox': json.loads(bbox_json),
                'timestamp': timestamp
            }
        
        return None
    
    def get_face_statistics(self, global_id: str) -> Optional[Dict]:
        """Get face statistics for a global ID."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT total_faces, avg_quality, last_seen, best_face_quality
            FROM face_statistics
            WHERE global_id = ?
        ''', (global_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            return {
                'total_faces': result[0],
                'avg_quality': float(result[1]),
                'last_seen': result[2],
                'best_quality': float(result[3])
            }
        
        return None
    
    def get_gallery_statistics(self) -> Dict:
        """Get overall face gallery statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Total faces
        cursor.execute('SELECT COUNT(*) FROM face_profiles')
        total_faces = cursor.fetchone()[0]
        
        # Unique global IDs with faces
        cursor.execute('SELECT COUNT(DISTINCT global_id) FROM face_profiles')
        unique_identities = cursor.fetchone()[0]
        
        # Average face quality
        cursor.execute('SELECT AVG(face_quality) FROM face_profiles')
        avg_quality = cursor.fetchone()[0] or 0.0
        
        # Recent additions (last 24 hours)
        cursor.execute('''
            SELECT COUNT(*) FROM face_profiles
            WHERE timestamp >= datetime('now', '-1 day')
        ''')
        recent_faces = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_faces': total_faces,
            'unique_identities': unique_identities,
            'avg_quality': float(avg_quality),
            'recent_faces': recent_faces
        }