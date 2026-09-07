# reid/reid_gallery.py
import numpy as np
from typing import Dict, List, Tuple, Optional
from collections import defaultdict
from datetime import datetime
import sqlite3
import json

class ReIDGallery:
    """Gallery for cross-camera Re-ID matching."""
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self.gallery = {}  # track_id -> embedding
        self.global_ids = {}  # track_id -> global_person_id
        self.camera_profiles = defaultdict(dict)  # camera_id -> {track_id: embedding}
        self._init_database()
        
    def _init_database(self):
        """Initialize Re-ID database tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Drop existing tables if they exist (clean start)
        cursor.execute('DROP TABLE IF EXISTS reid_profiles')
        cursor.execute('DROP TABLE IF EXISTS reid_matches')
        cursor.execute('DROP TABLE IF EXISTS global_identities')
        
        # Create new tables
        cursor.execute('''
            CREATE TABLE global_identities (
                global_id TEXT PRIMARY KEY,
                created_at DATETIME,
                last_updated DATETIME,
                embedding BLOB,
                camera_count INTEGER DEFAULT 0,
                track_count INTEGER DEFAULT 0,
                metadata TEXT
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE reid_profiles (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                camera_id INTEGER,
                track_id TEXT,
                embedding BLOB,
                quality REAL,
                timestamp DATETIME,
                similarity_score REAL,
                FOREIGN KEY (global_id) REFERENCES global_identities(global_id)
            )
        ''')
        
        cursor.execute('''
            CREATE TABLE reid_matches (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                camera_id INTEGER,
                track_id TEXT,
                similarity REAL,
                matched_at DATETIME,
                confidence INTEGER,
                FOREIGN KEY (global_id) REFERENCES global_identities(global_id)
            )
        ''')
        
        conn.commit()
        conn.close()
        
    def add_observation(self, camera_id: int, track_id: str,
                       embedding: np.ndarray, quality: float,
                       timestamp: datetime) -> Optional[str]:
        """
        Add a Re-ID observation and match to existing identity.
        
        Returns:
            Global ID if matched, None if new identity created
        """
        # Store in memory
        self.camera_profiles[camera_id][track_id] = {
            'embedding': embedding,
            'quality': quality,
            'timestamp': timestamp
        }
        
        # Try to match with existing identities
        global_id = self._match_existing_identity(embedding, camera_id, track_id)
        
        if global_id is None:
            # Create new identity
            global_id = self._create_global_identity(embedding, camera_id, track_id)
            
        # Store in database
        self._store_profile(global_id, camera_id, track_id, 
                           embedding, quality, timestamp)
        
        return global_id
    
    def _match_existing_identity(self, embedding: np.ndarray,
                                camera_id: int, track_id: str) -> Optional[str]:
        """Match embedding against existing identities."""
        # Get candidates from other cameras
        candidates = self._get_candidates(camera_id)
        
        if not candidates:
            return None
            
        best_match = None
        best_score = 0
        threshold = 0.55
        
        for global_id, candidate_data in candidates.items():
            candidate_emb = candidate_data['embedding']
            score = self._compute_similarity(embedding, candidate_emb)
            
            # Quality weighting
            quality = candidate_data.get('quality', 0.5)
            score = score * (0.7 + 0.3 * quality)
            
            if score > best_score and score > threshold:
                best_score = score
                best_match = global_id
                
        if best_match is not None:
            # Update match in database
            conn = sqlite3.connect(self.db_path)
            cursor = conn.cursor()
            cursor.execute('''
                INSERT INTO reid_matches
                (global_id, camera_id, track_id, similarity, matched_at, confidence)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (best_match, camera_id, track_id, best_score, 
                 datetime.now(), 1))
            conn.commit()
            conn.close()
            
        return best_match
    
    def _get_candidates(self, exclude_camera_id: int) -> Dict:
        """Get candidate identities from other cameras."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Get unique global IDs from other cameras
        cursor.execute('''
            SELECT DISTINCT global_id, camera_id, embedding, quality
            FROM reid_profiles
            WHERE camera_id != ?
            ORDER BY timestamp DESC
        ''', (exclude_camera_id,))
        
        candidates = {}
        for global_id, cam_id, emb_bytes, quality in cursor.fetchall():
            if global_id not in candidates:
                embedding = np.frombuffer(emb_bytes, dtype=np.float32)
                candidates[global_id] = {
                    'embedding': embedding,
                    'quality': quality
                }
                
        conn.close()
        return candidates
    
    def _create_global_identity(self, embedding: np.ndarray,
                               camera_id: int, track_id: str) -> str:
        """Create a new global identity."""
        # Generate unique ID
        import uuid
        global_id = f"GLOB_{uuid.uuid4().hex[:8].upper()}"
        
        # Store in database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        emb_bytes = embedding.astype(np.float32).tobytes()
        cursor.execute('''
            INSERT INTO global_identities
            (global_id, created_at, last_updated, embedding, camera_count, track_count)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (global_id, datetime.now(), datetime.now(), emb_bytes, 1, 1))
        
        conn.commit()
        conn.close()
        
        print(f"🆔 Created new global identity: {global_id}")
        return global_id
    
    def _store_profile(self, global_id: str, camera_id: int,
                      track_id: str, embedding: np.ndarray,
                      quality: float, timestamp: datetime):
        """Store Re-ID profile in database."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        emb_bytes = embedding.astype(np.float32).tobytes()
        cursor.execute('''
            INSERT INTO reid_profiles
            (global_id, camera_id, track_id, embedding, quality, timestamp)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (global_id, camera_id, track_id, emb_bytes, quality, timestamp))
        
        conn.commit()
        conn.close()
    
    def _compute_similarity(self, emb1: np.ndarray, emb2: np.ndarray) -> float:
        """Compute cosine similarity."""
        if emb1.shape != emb2.shape:
            return 0.0
        return float(np.dot(emb1, emb2))
    
    def get_global_id(self, camera_id: int, track_id: str) -> Optional[str]:
        """Get global ID for a camera/track pair."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT global_id
            FROM reid_profiles
            WHERE camera_id = ? AND track_id = ?
            ORDER BY timestamp DESC
            LIMIT 1
        ''', (camera_id, track_id))
        
        result = cursor.fetchone()
        conn.close()
        
        return result[0] if result else None
    
    def get_statistics(self) -> dict:
        """Get gallery statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM global_identities')
        total_identities = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reid_profiles')
        total_profiles = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM reid_matches')
        total_matches = cursor.fetchone()[0]
        
        conn.close()
        
        return {
            'total_identities': total_identities,
            'total_profiles': total_profiles,
            'total_matches': total_matches,
            'camera_profiles': {
                cam: len(profiles) 
                for cam, profiles in self.camera_profiles.items()
            }
        }