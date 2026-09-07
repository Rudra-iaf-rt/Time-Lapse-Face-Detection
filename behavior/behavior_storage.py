# behavior/behavior_storage.py
import sqlite3
import json
from typing import Dict, List, Optional, Any
from datetime import datetime

class BehaviorStorage:
    """
    Store and retrieve behavioral data.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self):
        """Initialize behavior tables."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Behavior profiles
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_profiles (
                global_id TEXT PRIMARY KEY,
                profile_data TEXT,  # JSON
                created_at DATETIME,
                last_updated DATETIME
            )
        ''')
        
        # Anomalies
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_anomalies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                anomaly_type TEXT,
                severity TEXT,
                description TEXT,
                details TEXT,  # JSON
                confidence REAL,
                detected_at DATETIME,
                resolved BOOLEAN DEFAULT 0,
                resolved_at DATETIME,
                FOREIGN KEY (global_id) REFERENCES behavior_profiles(global_id)
            )
        ''')
        
        # Behavioral patterns
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavioral_patterns (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                pattern_type TEXT,
                pattern_data TEXT,  # JSON
                confidence REAL,
                created_at DATETIME,
                expires_at DATETIME
            )
        ''')
        
        # Behavior metrics
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS behavior_metrics (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                global_id TEXT,
                metric_name TEXT,
                metric_value REAL,
                timestamp DATETIME,
                metadata TEXT,  # JSON
                FOREIGN KEY (global_id) REFERENCES behavior_profiles(global_id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def store_profile(self, global_id: str, profile_data: Dict):
        """Store behavioral profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT OR REPLACE INTO behavior_profiles
            (global_id, profile_data, created_at, last_updated)
            VALUES (?, ?, COALESCE(
                (SELECT created_at FROM behavior_profiles WHERE global_id = ?),
                ?),
                ?)
        ''', (global_id, json.dumps(profile_data), global_id, 
              datetime.now().isoformat(), datetime.now().isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_profile(self, global_id: str) -> Optional[Dict]:
        """Get behavioral profile."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT profile_data, created_at, last_updated
            FROM behavior_profiles
            WHERE global_id = ?
        ''', (global_id,))
        
        result = cursor.fetchone()
        conn.close()
        
        if result:
            profile = json.loads(result[0])
            profile['created_at'] = result[1]
            profile['last_updated'] = result[2]
            return profile
        
        return None
    
    def store_anomaly(self, global_id: str, anomaly: Dict):
        """Store detected anomaly."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO behavior_anomalies
            (global_id, anomaly_type, severity, description,
             details, confidence, detected_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        ''', (
            global_id,
            anomaly.get('type'),
            anomaly.get('severity'),
            anomaly.get('description'),
            json.dumps(anomaly.get('details', {})),
            anomaly.get('confidence', 0),
            datetime.now().isoformat()
        ))
        
        conn.commit()
        conn.close()
    
    def get_anomalies(self, global_id: Optional[str] = None,
                      start_time: Optional[datetime] = None,
                      end_time: Optional[datetime] = None,
                      severity: Optional[str] = None) -> List[Dict]:
        """Get anomalies with filters."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT global_id, anomaly_type, severity, description,
                   details, confidence, detected_at, resolved
            FROM behavior_anomalies
            WHERE 1=1
        '''
        params = []
        
        if global_id:
            query += ' AND global_id = ?'
            params.append(global_id)
        
        if start_time:
            query += ' AND detected_at >= ?'
            params.append(start_time.isoformat())
        
        if end_time:
            query += ' AND detected_at <= ?'
            params.append(end_time.isoformat())
        
        if severity:
            query += ' AND severity = ?'
            params.append(severity)
        
        query += ' ORDER BY detected_at DESC'
        
        cursor.execute(query, params)
        
        anomalies = []
        for row in cursor.fetchall():
            anomalies.append({
                'global_id': row[0],
                'type': row[1],
                'severity': row[2],
                'description': row[3],
                'details': json.loads(row[4]) if row[4] else {},
                'confidence': row[5],
                'detected_at': row[6],
                'resolved': bool(row[7])
            })
        
        conn.close()
        return anomalies
    
    def store_pattern(self, pattern_type: str, pattern_data: Dict,
                      confidence: float, expires_in_days: int = 30):
        """Store behavioral pattern."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        expires_at = datetime.now() + timedelta(days=expires_in_days)
        
        cursor.execute('''
            INSERT INTO behavioral_patterns
            (pattern_type, pattern_data, confidence, created_at, expires_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (pattern_type, json.dumps(pattern_data), confidence,
              datetime.now().isoformat(), expires_at.isoformat()))
        
        conn.commit()
        conn.close()
    
    def get_patterns(self, pattern_type: Optional[str] = None) -> List[Dict]:
        """Get behavioral patterns."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT pattern_type, pattern_data, confidence,
                   created_at, expires_at
            FROM behavioral_patterns
            WHERE expires_at > datetime('now')
        '''
        params = []
        
        if pattern_type:
            query += ' AND pattern_type = ?'
            params.append(pattern_type)
        
        cursor.execute(query, params)
        
        patterns = []
        for row in cursor.fetchall():
            patterns.append({
                'type': row[0],
                'data': json.loads(row[1]),
                'confidence': row[2],
                'created_at': row[3],
                'expires_at': row[4]
            })
        
        conn.close()
        return patterns
    
    def store_metric(self, global_id: str, metric_name: str,
                     metric_value: float, metadata: Dict = None):
        """Store behavior metric."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO behavior_metrics
            (global_id, metric_name, metric_value, timestamp, metadata)
            VALUES (?, ?, ?, ?, ?)
        ''', (global_id, metric_name, metric_value,
              datetime.now().isoformat(),
              json.dumps(metadata or {})))
        
        conn.commit()
        conn.close()
    
    def get_metrics(self, global_id: str, metric_name: Optional[str] = None,
                    start_time: Optional[datetime] = None,
                    end_time: Optional[datetime] = None) -> List[Dict]:
        """Get behavior metrics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        query = '''
            SELECT metric_name, metric_value, timestamp, metadata
            FROM behavior_metrics
            WHERE global_id = ?
        '''
        params = [global_id]
        
        if metric_name:
            query += ' AND metric_name = ?'
            params.append(metric_name)
        
        if start_time:
            query += ' AND timestamp >= ?'
            params.append(start_time.isoformat())
        
        if end_time:
            query += ' AND timestamp <= ?'
            params.append(end_time.isoformat())
        
        query += ' ORDER BY timestamp DESC'
        
        cursor.execute(query, params)
        
        metrics = []
        for row in cursor.fetchall():
            metrics.append({
                'name': row[0],
                'value': row[1],
                'timestamp': row[2],
                'metadata': json.loads(row[3]) if row[3] else {}
            })
        
        conn.close()
        return metrics