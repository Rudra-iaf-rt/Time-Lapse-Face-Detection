# search/query_engine.py
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime
import json

from .query_builder import SearchQuery, QueryBuilder
from .search_index import SearchIndex
from .filters import FilterProcessor
from .aggregators import ResultAggregator

class QueryEngine:
    """
    Main search engine for intelligent querying.
    """
    
    def __init__(self, db_path: str = "database/identities.db"):
        self.db_path = db_path
        self.index = SearchIndex(db_path)
        self.filter_processor = FilterProcessor()
        self.aggregator = ResultAggregator()
        
    def search(self, query: SearchQuery) -> Dict:
        """
        Execute a search query.
        
        Returns:
            Dictionary with results and metadata
        """
        # Convert query to dict for index search
        query_dict = self._query_to_dict(query)
        
        # Determine what to search for
        results = []
        result_type = None
        
        # Check if we're searching for specific types
        if query.event.event_types or query.event.min_duration is not None:
            # Search events
            results = self.index.search_events(query_dict)
            result_type = 'events'
        elif query.spatial.transition_filter:
            # Search transitions
            results = self.index.search_transitions(query_dict)
            result_type = 'transitions'
        else:
            # Search persons
            results = self.index.search_persons(query_dict)
            result_type = 'persons'
        
        # Apply additional filters
        filtered_results = self.filter_processor.apply_filters(results, query)
        
        # Aggregate results
        aggregated = self.aggregator.aggregate(filtered_results, query)
        
        return {
            'results': filtered_results,
            'aggregated': aggregated,
            'result_type': result_type,
            'total_count': len(filtered_results),
            'query': query.to_dict(),
            'timestamp': datetime.now().isoformat()
        }
    
    def _query_to_dict(self, query: SearchQuery) -> Dict:
        """Convert search query to dict for index."""
        query_dict = {}
        
        # Time range
        if query.time_range.is_active():
            query_dict['time_range'] = {}
            if query.time_range.start:
                query_dict['time_range']['start'] = query.time_range.start.isoformat()
            if query.time_range.end:
                query_dict['time_range']['end'] = query.time_range.end.isoformat()
        
        # Spatial filters
        if query.spatial.cameras:
            query_dict['cameras'] = query.spatial.cameras
        if query.spatial.min_dwell_time is not None:
            query_dict['min_duration'] = query.spatial.min_dwell_time
        if query.spatial.max_dwell_time is not None:
            query_dict['max_duration'] = query.spatial.max_dwell_time
        
        # Person filters
        if query.person.global_ids:
            query_dict['global_ids'] = query.person.global_ids
        if query.person.min_confidence is not None:
            query_dict['min_confidence'] = query.person.min_confidence
        if query.person.face_available is not None:
            query_dict['face_available'] = query.person.face_available
        
        # Event filters
        if query.event.event_types:
            query_dict['event_types'] = query.event.event_types
        if query.event.min_duration is not None:
            query_dict['min_duration'] = query.event.min_duration
        if query.event.max_duration is not None:
            query_dict['max_duration'] = query.event.max_duration
        
        # Transition filters
        if query.spatial.transition_filter:
            transition = query.spatial.transition_filter
            query_dict['from_cameras'] = transition.get('from', [])
            query_dict['to_cameras'] = transition.get('to', [])
        
        # Sorting and limit
        query_dict['sort_by'] = query.sort_by
        query_dict['sort_order'] = query.sort_order.value.upper()
        query_dict['limit'] = query.limit
        query_dict['offset'] = query.offset
        
        return query_dict
    
    def search_by_text(self, text: str) -> Dict:
        """
        Natural language-like search.
        
        This is a simplified version - in production, use NLP.
        """
        query = QueryBuilder()
        text_lower = text.lower()
        
        # Time-based
        if 'today' in text_lower:
            query = query.with_last_days(1)
        elif 'yesterday' in text_lower:
            start = datetime.now().replace(hour=0, minute=0, second=0) - timedelta(days=1)
            end = start + timedelta(days=1)
            query = query.with_time_range(start, end)
        elif 'last hour' in text_lower:
            query = query.with_last_hours(1)
        
        # Camera-based
        if 'camera' in text_lower:
            # Extract camera numbers (simple regex)
            import re
            cameras = re.findall(r'camera\s*(\d+)', text_lower)
            if cameras:
                query = query.with_cameras([int(c) for c in cameras])
        
        # Duration-based
        if 'more than' in text_lower:
            import re
            times = re.findall(r'(\d+)\s*(minute|second)', text_lower)
            for num, unit in times:
                duration = float(num) * (60 if 'minute' in unit else 1)
                query = query.with_dwell_time(min_time=duration)
        
        # Person ID
        if 'person' in text_lower:
            import re
            persons = re.findall(r'person[_\s]*([A-Z0-9]+)', text_lower.upper())
            if persons:
                query = query.with_person(persons)
        
        return self.search(query.build())
    
    def get_statistics(self) -> Dict:
        """Get search index statistics."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        stats = {}
        
        # Count persons
        cursor.execute('SELECT COUNT(*) FROM search_person_index')
        stats['total_persons'] = cursor.fetchone()[0]
        
        # Count events
        cursor.execute('SELECT COUNT(*) FROM search_time_index')
        stats['total_events'] = cursor.fetchone()[0]
        
        # Count transitions
        cursor.execute('SELECT COUNT(*) FROM search_transition_index')
        stats['total_transitions'] = cursor.fetchone()[0]
        
        # Most active persons (top 10)
        cursor.execute('''
            SELECT global_id, total_duration
            FROM search_person_index
            ORDER BY total_duration DESC
            LIMIT 10
        ''')
        stats['most_active'] = [
            {'global_id': row[0], 'duration': row[1]}
            for row in cursor.fetchall()
        ]
        
        # Camera usage
        cursor.execute('''
            SELECT camera_id, COUNT(*) as count
            FROM search_camera_index
            GROUP BY camera_id
            ORDER BY count DESC
        ''')
        stats['camera_usage'] = {
            row[0]: row[1] for row in cursor.fetchall()
        }
        
        # Event type distribution
        cursor.execute('''
            SELECT event_type, COUNT(*) as count
            FROM search_time_index
            GROUP BY event_type
        ''')
        stats['event_distribution'] = {
            row[0]: row[1] for row in cursor.fetchall()
        }
        
        conn.close()
        return stats