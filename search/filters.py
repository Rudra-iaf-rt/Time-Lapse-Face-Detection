# search/filters.py
from typing import Dict, List, Any, Optional
from datetime import datetime
import json

from .query_builder import SearchQuery, ComparisonOperator

class FilterProcessor:
    """
    Apply filters to search results.
    """
    
    def apply_filters(self, results: List[Dict], query: SearchQuery) -> List[Dict]:
        """
        Apply all filters to results.
        """
        filtered = results
        
        # Apply custom conditions
        for condition in query.conditions:
            filtered = self._apply_condition(filtered, condition)
        
        # Apply spatial filters
        filtered = self._apply_spatial_filters(filtered, query.spatial)
        
        # Apply person filters
        filtered = self._apply_person_filters(filtered, query.person)
        
        # Apply event filters
        filtered = self._apply_event_filters(filtered, query.event)
        
        return filtered
    
    def _apply_condition(self, results: List[Dict], 
                        condition: Any) -> List[Dict]:
        """Apply a single condition."""
        field = condition.field
        operator = condition.operator
        value = condition.value
        value2 = condition.value2
        
        filtered = []
        for result in results:
            if field in result:
                field_value = result[field]
                
                if operator == ComparisonOperator.EQ:
                    if field_value == value:
                        filtered.append(result)
                elif operator == ComparisonOperator.NE:
                    if field_value != value:
                        filtered.append(result)
                elif operator == ComparisonOperator.GT:
                    if field_value > value:
                        filtered.append(result)
                elif operator == ComparisonOperator.LT:
                    if field_value < value:
                        filtered.append(result)
                elif operator == ComparisonOperator.GTE:
                    if field_value >= value:
                        filtered.append(result)
                elif operator == ComparisonOperator.LTE:
                    if field_value <= value:
                        filtered.append(result)
                elif operator == ComparisonOperator.BETWEEN:
                    if value <= field_value <= value2:
                        filtered.append(result)
                elif operator == ComparisonOperator.IN:
                    if field_value in value:
                        filtered.append(result)
                elif operator == ComparisonOperator.CONTAINS:
                    if value in str(field_value):
                        filtered.append(result)
            else:
                filtered.append(result)
        
        return filtered
    
    def _apply_spatial_filters(self, results: List[Dict],
                              spatial: Any) -> List[Dict]:
        """Apply spatial filters."""
        if not spatial.cameras:
            return results
        
        filtered = []
        for result in results:
            # Check cameras in result
            result_cameras = result.get('cameras_visited', [])
            if isinstance(result_cameras, str):
                result_cameras = json.loads(result_cameras)
            
            # Check if any camera matches
            match = False
            for camera in spatial.cameras:
                if camera in result_cameras:
                    match = True
                    break
            
            if match:
                filtered.append(result)
        
        return filtered
    
    def _apply_person_filters(self, results: List[Dict],
                             person: Any) -> List[Dict]:
        """Apply person filters."""
        filtered = results
        
        # Global ID filter
        if person.global_ids:
            filtered = [
                r for r in filtered
                if r.get('global_id') in person.global_ids
            ]
        
        # Confidence filter
        if person.min_confidence is not None:
            filtered = [
                r for r in filtered
                if r.get('confidence', 0) >= person.min_confidence
            ]
        
        if person.max_confidence is not None:
            filtered = [
                r for r in filtered
                if r.get('confidence', 1) <= person.max_confidence
            ]
        
        # Face availability
        if person.face_available is not None:
            if person.face_available:
                filtered = [
                    r for r in filtered
                    if r.get('face_count', 0) > 0
                ]
            else:
                filtered = [
                    r for r in filtered
                    if r.get('face_count', 0) == 0
                ]
        
        return filtered
    
    def _apply_event_filters(self, results: List[Dict],
                            event: Any) -> List[Dict]:
        """Apply event filters."""
        if not event.event_types:
            return results
        
        filtered = []
        for result in results:
            # Check if result has event_type field
            event_type = result.get('event_type')
            if event_type and event_type in event.event_types:
                filtered.append(result)
            
            # Also check if result has events in metadata
            metadata = result.get('metadata', {})
            if isinstance(metadata, str):
                metadata = json.loads(metadata)
            
            events = metadata.get('events', [])
            for ev in events:
                if ev.get('type') in event.event_types:
                    filtered.append(result)
                    break
        
        return filtered