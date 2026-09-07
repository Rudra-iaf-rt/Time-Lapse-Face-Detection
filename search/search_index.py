# search/search_index.py
import sqlite3
import json
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
from collections import defaultdict
import numpy as np

class SearchIndex:
    """
    Index for fast searching of person tracking data.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self._init_index_tables()
        self._load_index()
    
    def _init_index_tables(self):
        """Initialize index tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Person index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_person_index (
                global_id TEXT PRIMARY KEY,
                first_seen DATETIME,
                last_seen DATETIME,
                total_duration REAL,
                cameras_visited TEXT,  # JSON
                route TEXT,  # JSON
                confidence REAL,
                face_count INTEGER,
                reid_count INTEGER,
                last_updated DATETIME
            )
        ''')
        
        # Camera index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_camera_index (
                camera_id INTEGER,
                global_id TEXT,
                start_time DATETIME,
                end_time DATETIME,
                duration REAL,
                confidence REAL,
                PRIMARY KEY (camera_id, global_id, start_time)
            )
        ''')
        
        # Time index (for fast time-based queries)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_time_index (
                global_id TEXT,
                timestamp DATETIME,
                camera_id INTEGER,
                event_type TEXT,
                metadata TEXT,  # JSON
                PRIMARY KEY (global_id, timestamp)
            )
        ''')
        
        # Transition index
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS search_transition_index (
                from_camera INTEGER,
                to_camera INTEGER,
                global_id TEXT,
                transition_time DATETIME,
                duration REAL,
                confidence REAL,
                PRIMARY KEY (from_camera, to_camera, global_id, transition_time)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def _load_index(self):
        """Load existing index data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load person index
        cursor.execute('''
            SELECT global_id, first_seen, last_seen, total_duration,
                   cameras_visited, route, confidence, face_count, reid_count
            FROM search_person_index
        ''')
        
        self.person_index = {}
        for row in cursor.fetchall():
            self.person_index[row[0]] = {
                'first_seen': datetime.fromisoformat(row[1]) if row[1] else None,
                'last_seen': datetime.fromisoformat(row[2]) if row[2] else None,
                'total_duration': row[3],
                'cameras_visited': json.loads(row[4]) if row[4] else [],
                'route': json.loads(row[5]) if row[5] else [],
                'confidence': row[6],
                'face_count': row[7],
                'reid_count': row[8]
            }
        
        conn.close()
    
    def index_person(self, global_id: str, timeline_data: Dict):
        """
        Index a person's timeline data.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_person_index
            (global_id, first_seen, last_seen, total_duration,
             cameras_visited, route, confidence, face_count, reid_count,
             last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            global_id,
            timeline_data.get('first_seen'),
            timeline_data.get('last_seen'),
            timeline_data.get('total_duration', 0),
            json.dumps(timeline_data.get('cameras_visited', [])),
            json.dumps(timeline_data.get('route', [])),
            timeline_data.get('confidence', 0.5),
            timeline_data.get('face_count', 0),
            timeline_data.get('reid_count', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
        
        # Update in-memory index
        self.person_index[global_id] = {
            'first_seen': timeline_data.get('first_seen'),
            'last_seen': timeline_data.get('last_seen'),
            'total_duration': timeline_data.get('total_duration', 0),
            'cameras_visited': timeline_data.get('cameras_visited', []),
            'route': timeline_data.get('route', []),
            'confidence': timeline_data.get('confidence', 0.5),
            'face_count': timeline_data.get('face_count', 0),
            'reid_count': timeline_data.get('reid_count', 0)
        }
    
    def index_camera_visit(self, camera_id: int, global_id: str,
                          start_time: datetime, end_time: datetime,
                          confidence: float):
        """
        Index a camera visit.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        duration = (end_time - start_time).total_seconds()
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_camera_index
            (camera_id, global_id, start_time, end_time, duration, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (camera_id, global_id, start_time.isoformat(), end_time.isoformat(),
              duration, confidence))
        
        conn.commit()
        conn.close()
    
    def index_event(self, global_id: str, timestamp: datetime,
                   camera_id: int, event_type: str, metadata: Dict = None):
        """
        Index an event.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_time_index
            (global_id, timestamp, camera_id, event_type, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (global_id, timestamp.isoformat(), camera_id, event_type,
              json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
    
    def index_transition(self, from_camera: int, to_camera: int,
                        global_id: str, transition_time: datetime,
                        duration: float, confidence: float):
        """
        Index a camera transition.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO search_transition_index
            (from_camera, to_camera, global_id, transition_time, duration, confidence)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (from_camera, to_camera, global_id, transition_time.isoformat(),
              duration, confidence))
        
        conn.commit()
        conn.close()
    
    def search_persons(self, query: Dict) -> List[Dict]:
        """
        Search for persons matching query.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT global_id, first_seen, last_seen, total_duration,
                   cameras_visited, route, confidence, face_count, reid_count
            FROM search_person_index
            WHERE 1=1
        '''
        params = []
        
        # Time range
        if query.get('time_range'):
            if query['time_range'].get('start'):
                sql += ' AND last_seen >= ?'
                params.append(query['time_range']['start'])
            if query['time_range'].get('end'):
                sql += ' AND first_seen <= ?'
                params.append(query['time_range']['end'])
        
        # Camera filter
        if query.get('cameras'):
            sql += ' AND ('
            for i, cam in enumerate(query['cameras']):
                if i > 0:
                    sql += ' OR'
                sql += ' cameras_visited LIKE ?'
                params.append(f'%"{cam}"%')
            sql += ')'
        
        # Duration filter
        if query.get('min_duration') is not None:
            sql += ' AND total_duration >= ?'
            params.append(query['min_duration'])
        if query.get('max_duration') is not None:
            sql += ' AND total_duration <= ?'
            params.append(query['max_duration'])
        
        # Confidence filter
        if query.get('min_confidence') is not None:
            sql += ' AND confidence >= ?'
            params.append(query['min_confidence'])
        
        # Face availability
        if query.get('face_available') is not None:
            if query['face_available']:
                sql += ' AND face_count > 0'
            else:
                sql += ' AND face_count = 0'
        
        # Sorting
        sort_field = query.get('sort_by', 'last_seen')
        sort_order = query.get('sort_order', 'DESC')
        sql += f' ORDER BY {sort_field} {sort_order}'
        
        # Limit
        if query.get('limit'):
            sql += ' LIMIT ?'
            params.append(query['limit'])
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'global_id': row[0],
                'first_seen': row[1],
                'last_seen': row[2],
                'total_duration': row[3],
                'cameras_visited': json.loads(row[4]) if row[4] else [],
                'route': json.loads(row[5]) if row[5] else [],
                'confidence': row[6],
                'face_count': row[7],
                'reid_count': row[8]
            })
        
        conn.close()
        return results
    
    def search_events(self, query: Dict) -> List[Dict]:
        """
        Search for events matching query.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT global_id, timestamp, camera_id, event_type, metadata
            FROM search_time_index
            WHERE 1=1
        '''
        params = []
        
        # Time range
        if query.get('start_time'):
            sql += ' AND timestamp >= ?'
            params.append(query['start_time'])
        if query.get('end_time'):
            sql += ' AND timestamp <= ?'
            params.append(query['end_time'])
        
        # Camera filter
        if query.get('cameras'):
            sql += f' AND camera_id IN ({",".join(["?"] * len(query["cameras"]))})'
            params.extend(query['cameras'])
        
        # Event type
        if query.get('event_types'):
            sql += f' AND event_type IN ({",".join(["?"] * len(query["event_types"]))})'
            params.extend(query['event_types'])
        
        # Person filter
        if query.get('global_ids'):
            sql += f' AND global_id IN ({",".join(["?"] * len(query["global_ids"]))})'
            params.extend(query['global_ids'])
        
        # Sorting
        sql += ' ORDER BY timestamp DESC'
        
        # Limit
        if query.get('limit'):
            sql += ' LIMIT ?'
            params.append(query['limit'])
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'global_id': row[0],
                'timestamp': row[1],
                'camera_id': row[2],
                'event_type': row[3],
                'metadata': json.loads(row[4]) if row[4] else {}
            })
        
        conn.close()
        return results
    
    def search_transitions(self, query: Dict) -> List[Dict]:
        """
        Search for camera transitions.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        sql = '''
            SELECT from_camera, to_camera, global_id, transition_time,
                   duration, confidence
            FROM search_transition_index
            WHERE 1=1
        '''
        params = []
        
        # From camera
        if query.get('from_cameras'):
            sql += f' AND from_camera IN ({",".join(["?"] * len(query["from_cameras"]))})'
            params.extend(query['from_cameras'])
        
        # To camera
        if query.get('to_cameras'):
            sql += f' AND to_camera IN ({",".join(["?"] * len(query["to_cameras"]))})'
            params.extend(query['to_cameras'])
        
        # Person filter
        if query.get('global_ids'):
            sql += f' AND global_id IN ({",".join(["?"] * len(query["global_ids"]))})'
            params.extend(query['global_ids'])
        
        # Time range
        if query.get('start_time'):
            sql += ' AND transition_time >= ?'
            params.append(query['start_time'])
        if query.get('end_time'):
            sql += ' AND transition_time <= ?'
            params.append(query['end_time'])
        
        # Duration filter
        if query.get('min_duration') is not None:
            sql += ' AND duration >= ?'
            params.append(query['min_duration'])
        if query.get('max_duration') is not None:
            sql += ' AND duration <= ?'
            params.append(query['max_duration'])
        
        sql += ' ORDER BY transition_time DESC'
        
        if query.get('limit'):
            sql += ' LIMIT ?'
            params.append(query['limit'])
        
        cursor.execute(sql, params)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'from_camera': row[0],
                'to_camera': row[1],
                'global_id': row[2],
                'transition_time': row[3],
                'duration': row[4],
                'confidence': row[5]
            })
        
        conn.close()
        return results