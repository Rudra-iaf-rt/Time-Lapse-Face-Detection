# timeline/timeline_storage.py
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

from .timeline_builder import PersonTimeline, TimelineSegment, TimelineEvent

class TimelineStorage:
    """
    Store and retrieve person timelines from database.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize timeline tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Timelines table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS person_timelines (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT UNIQUE,
                first_seen DATETIME,
                last_seen DATETIME,
                total_duration REAL,
                cameras_visited TEXT,  # JSON list
                route TEXT,  # JSON list
                metadata TEXT,  # JSON
                last_updated DATETIME
            )
        ''')
        
        # Segments table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeline_segments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                camera_id INTEGER,
                start_time DATETIME,
                end_time DATETIME,
                duration REAL,
                confidence REAL,
                events TEXT,  # JSON
                metadata TEXT,  # JSON
                FOREIGN KEY (global_id) REFERENCES person_timelines(global_id)
            )
        ''')
        
        # Timeline events table (denormalized for faster querying)
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS timeline_events (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                event_type TEXT,
                camera_id INTEGER,
                timestamp DATETIME,
                duration REAL,
                confidence REAL,
                metadata TEXT,  # JSON
                FOREIGN KEY (global_id) REFERENCES person_timelines(global_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_timeline(self, timeline: PersonTimeline):
        """
        Store a person timeline in the database.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Store main timeline
        cursor.execute('''
            INSERT OR REPLACE INTO person_timelines
            (global_id, first_seen, last_seen, total_duration,
             cameras_visited, route, metadata, last_updated)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            timeline.global_id,
            timeline.first_seen.isoformat() if timeline.first_seen else None,
            timeline.last_seen.isoformat() if timeline.last_seen else None,
            timeline.total_duration,
            json.dumps(timeline.cameras_visited),
            json.dumps(timeline.route),
            json.dumps(timeline.metadata),
            datetime.now().isoformat()
        ))
        
        # Store segments
        cursor.execute('DELETE FROM timeline_segments WHERE global_id = ?', 
                      (timeline.global_id,))
        
        for segment in timeline.segments:
            cursor.execute('''
                INSERT INTO timeline_segments
                (global_id, camera_id, start_time, end_time, duration,
                 confidence, events, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                timeline.global_id,
                segment.camera_id,
                segment.start_time.isoformat(),
                segment.end_time.isoformat(),
                segment.duration,
                segment.confidence,
                json.dumps([{
                    'event_type': e.event_type,
                    'timestamp': e.timestamp.isoformat(),
                    'duration': e.duration,
                    'confidence': e.confidence
                } for e in segment.events]),
                json.dumps(segment.metadata)
            ))
        
        # Store events
        cursor.execute('DELETE FROM timeline_events WHERE global_id = ?', 
                      (timeline.global_id,))
        
        for event in timeline.events:
            cursor.execute('''
                INSERT INTO timeline_events
                (global_id, event_type, camera_id, timestamp, duration,
                 confidence, metadata)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            ''', (
                timeline.global_id,
                event.event_type,
                event.camera_id,
                event.timestamp.isoformat(),
                event.duration,
                event.confidence,
                json.dumps(event.metadata)
            ))
        
        conn.commit()
        conn.close()
    
    def load_timeline(self, global_id: str) -> Optional[PersonTimeline]:
        """
        Load a person timeline from the database.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Load main timeline
        cursor.execute('''
            SELECT first_seen, last_seen, total_duration,
                   cameras_visited, route, metadata
            FROM person_timelines
            WHERE global_id = ?
        ''', (global_id,))
        
        result = cursor.fetchone()
        if not result:
            conn.close()
            return None
        
        # Load segments
        cursor.execute('''
            SELECT camera_id, start_time, end_time, duration,
                   confidence, events, metadata
            FROM timeline_segments
            WHERE global_id = ?
            ORDER BY start_time
        ''', (global_id,))
        
        segments = []
        for row in cursor.fetchall():
            events_data = json.loads(row[5])
            events = [
                TimelineEvent(
                    event_type=e['event_type'],
                    camera_id=row[0],
                    timestamp=datetime.fromisoformat(e['timestamp']),
                    duration=e.get('duration'),
                    confidence=e.get('confidence', 0.0)
                )
                for e in events_data
            ]
            
            segment = TimelineSegment(
                camera_id=row[0],
                start_time=datetime.fromisoformat(row[1]),
                end_time=datetime.fromisoformat(row[2]),
                duration=row[3],
                confidence=row[4],
                events=events,
                metadata=json.loads(row[6])
            )
            segments.append(segment)
        
        # Load events
        cursor.execute('''
            SELECT event_type, camera_id, timestamp, duration,
                   confidence, metadata
            FROM timeline_events
            WHERE global_id = ?
            ORDER BY timestamp
        ''', (global_id,))
        
        events = []
        for row in cursor.fetchall():
            event = TimelineEvent(
                event_type=row[0],
                camera_id=row[1],
                timestamp=datetime.fromisoformat(row[2]),
                duration=row[3],
                confidence=row[4],
                metadata=json.loads(row[5])
            )
            events.append(event)
        
        conn.close()
        
        # Build timeline
        timeline = PersonTimeline(
            global_id=global_id,
            segments=segments,
            events=events,
            first_seen=datetime.fromisoformat(result[0]) if result[0] else None,
            last_seen=datetime.fromisoformat(result[1]) if result[1] else None,
            total_duration=result[2],
            cameras_visited=json.loads(result[3]),
            route=json.loads(result[4]),
            metadata=json.loads(result[5])
        )
        
        return timeline
    
    def search_timelines(self, start_time: Optional[datetime] = None,
                        end_time: Optional[datetime] = None,
                        camera_id: Optional[int] = None,
                        min_duration: Optional[float] = None) -> List[str]:
        """
        Search for timelines matching criteria.
        """
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT DISTINCT global_id
            FROM person_timelines
            WHERE 1=1
        '''
        params = []
        
        if start_time:
            query += ' AND last_seen >= ?'
            params.append(start_time.isoformat())
        
        if end_time:
            query += ' AND first_seen <= ?'
            params.append(end_time.isoformat())
        
        if min_duration:
            query += ' AND total_duration >= ?'
            params.append(min_duration)
        
        if camera_id is not None:
            query += '''
                AND global_id IN (
                    SELECT global_id 
                    FROM timeline_segments 
                    WHERE camera_id = ?
                )
            '''
            params.append(camera_id)
        
        cursor.execute(query, params)
        
        results = [row[0] for row in cursor.fetchall()]
        conn.close()
        
        return results