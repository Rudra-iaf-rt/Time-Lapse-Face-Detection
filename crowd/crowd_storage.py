# crowd/crowd_storage.py
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta

class CrowdStorage:
    """
    Store and retrieve crowd metrics.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize crowd tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Crowd metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crowd_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                timestamp DATETIME,
                occupancy INTEGER,
                capacity INTEGER,
                occupancy_percentage REAL,
                entry_rate REAL,
                exit_rate REAL,
                dwell_time_avg REAL,
                crowd_density REAL,
                flow_rate REAL,
                congestion_level TEXT,
                metadata TEXT  # JSON
            )
        ''')
        
        # Crowd trends
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crowd_trends (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                period TEXT,
                trend_data TEXT,  # JSON
                peak_time DATETIME,
                peak_occupancy INTEGER,
                average_occupancy REAL,
                trend_direction TEXT,
                computed_at DATETIME
            )
        ''')
        
        # Occupancy alerts
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS occupancy_alerts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                camera_id INTEGER,
                timestamp DATETIME,
                occupancy INTEGER,
                capacity INTEGER,
                utilization REAL,
                severity TEXT,
                message TEXT,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME
            )
        ''')
        
        # Flow data
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS crowd_flow (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                from_camera INTEGER,
                to_camera INTEGER,
                person_id TEXT,
                timestamp DATETIME,
                duration REAL,
                metadata TEXT  # JSON
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_metrics(self, metrics: Dict):
        """Store crowd metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO crowd_metrics
            (camera_id, timestamp, occupancy, capacity, occupancy_percentage,
             entry_rate, exit_rate, dwell_time_avg, crowd_density,
             flow_rate, congestion_level, metadata)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            metrics.get('camera_id'),
            metrics.get('timestamp'),
            metrics.get('occupancy'),
            metrics.get('capacity'),
            metrics.get('occupancy_percentage'),
            metrics.get('entry_rate'),
            metrics.get('exit_rate'),
            metrics.get('dwell_time_avg'),
            metrics.get('crowd_density'),
            metrics.get('flow_rate'),
            metrics.get('congestion_level'),
            json.dumps(metrics.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def get_metrics(self, camera_id: Optional[int] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None,
                    limit: int = 1000) -> List[Dict]:
        """Get crowd metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT camera_id, timestamp, occupancy, capacity,
                   occupancy_percentage, entry_rate, exit_rate,
                   dwell_time_avg, crowd_density, flow_rate,
                   congestion_level, metadata
            FROM crowd_metrics
            WHERE 1=1
        '''
        params = []
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())
        
        query += ' ORDER BY timestamp DESC LIMIT ?'
        params.append(limit)
        
        cursor.execute(query, params)
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                'camera_id': row[0],
                'timestamp': row[1],
                'occupancy': row[2],
                'capacity': row[3],
                'occupancy_percentage': row[4],
                'entry_rate': row[5],
                'exit_rate': row[6],
                'dwell_time_avg': row[7],
                'crowd_density': row[8],
                'flow_rate': row[9],
                'congestion_level': row[10],
                'metadata': json.loads(row[11]) if row[11] else {}
            })
        
        conn.close()
        return metrics
    
    def store_trend(self, trend: Dict):
        """Store crowd trend."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO crowd_trends
            (camera_id, period, trend_data, peak_time,
             peak_occupancy, average_occupancy, trend_direction,
             computed_at)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            trend.get('camera_id'),
            trend.get('period'),
            json.dumps(trend.get('data', {})),
            trend.get('peak_time'),
            trend.get('peak_occupancy'),
            trend.get('average_occupancy'),
            trend.get('trend_direction'),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def store_alert(self, alert: Dict):
        """Store occupancy alert."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO occupancy_alerts
            (camera_id, timestamp, occupancy, capacity,
             utilization, severity, message)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            alert.get('camera_id'),
            alert.get('timestamp'),
            alert.get('occupancy'),
            alert.get('capacity'),
            alert.get('utilization'),
            alert.get('severity'),
            alert.get('message')
        ))
        
        conn.commit()
        conn.close()
    
    def store_flow(self, flow: Dict):
        """Store crowd flow data."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO crowd_flow
            (from_camera, to_camera, person_id,
             timestamp, duration, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            flow.get('from_camera'),
            flow.get('to_camera'),
            flow.get('person_id'),
            flow.get('timestamp'),
            flow.get('duration'),
            json.dumps(flow.get('metadata', {}))
        ))
        
        conn.commit()
        conn.close()
    
    def get_alerts(self, resolved: bool = False,
                   camera_id: Optional[int] = None,
                   severity: Optional[str] = None) -> List[Dict]:
        """Get occupancy alerts."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT camera_id, timestamp, occupancy, capacity,
                   utilization, severity, message, resolved, resolved_at
            FROM occupancy_alerts
            WHERE resolved = ?
        '''
        params = [1 if resolved else 0]
        
        if camera_id is not None:
            query += ' AND camera_id = ?'
            params.append(camera_id)
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY timestamp DESC'
        
        cursor.execute(query, params)
        
        alerts = []
        for row in cursor.fetchall():
            alerts.append({
                'camera_id': row[0],
                'timestamp': row[1],
                'occupancy': row[2],
                'capacity': row[3],
                'utilization': row[4],
                'severity': row[5],
                'message': row[6],
                'resolved': bool(row[7]),
                'resolved_at': row[8]
            })
        
        conn.close()
        return alerts