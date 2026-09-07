# database/models.py
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime
import json

Base = declarative_base()

class Person(Base):
    __tablename__ = 'persons'
    
    id = Column(Integer, primary_key=True)
    global_id = Column(String(50), unique=True, nullable=False, index=True)
    first_seen = Column(DateTime, nullable=False)
    last_seen = Column(DateTime, nullable=False)
    confidence = Column(Float, default=0.5)
    # Column name 'metadata' reserved on Declarative API — map to person_metadata
    person_metadata = Column('metadata', JSON, default={})
    
    # Relationships
    biometric_profiles = relationship("BiometricProfile", back_populates="person")
    tracks = relationship("Track", back_populates="person")
    observations = relationship("Observation", back_populates="person")
    
    def to_dict(self):
        return {
            'id': self.id,
            'global_id': self.global_id,
            'first_seen': self.first_seen.isoformat() if self.first_seen else None,
            'last_seen': self.last_seen.isoformat() if self.last_seen else None,
            'confidence': self.confidence,
            'metadata': self.person_metadata or {}
        }

class BiometricProfile(Base):
    __tablename__ = 'biometric_profiles'
    
    id = Column(Integer, primary_key=True)
    global_id = Column(String(50), ForeignKey('persons.global_id'), nullable=False, index=True)
    face_embedding = Column(Text, nullable=True)  # Stored as base64 or binary
    reid_embedding = Column(Text, nullable=True)
    appearance_embedding = Column(Text, nullable=True)
    face_quality = Column(Float, default=0.0)
    reid_quality = Column(Float, default=0.0)
    created_at = Column(DateTime, nullable=False)
    updated_at = Column(DateTime, nullable=False)
    
    # Relationship
    person = relationship("Person", back_populates="biometric_profiles")
    
    def to_dict(self):
        return {
            'id': self.id,
            'global_id': self.global_id,
            'face_quality': self.face_quality,
            'reid_quality': self.reid_quality,
            'created_at': self.created_at.isoformat() if self.created_at else None,
            'updated_at': self.updated_at.isoformat() if self.updated_at else None
        }

class Camera(Base):
    __tablename__ = 'cameras'
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, unique=True, nullable=False, index=True)
    name = Column(String(100), nullable=False)
    location = Column(String(200), nullable=True)
    capacity = Column(Integer, default=100)
    camera_metadata = Column('metadata', JSON, default={})
    
    # Relationships
    tracks = relationship("Track", back_populates="camera")
    observations = relationship("Observation", back_populates="camera")
    
    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'name': self.name,
            'location': self.location,
            'capacity': self.capacity,
            'metadata': self.camera_metadata or {}
        }

class Track(Base):
    __tablename__ = 'tracks'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(String(50), unique=True, nullable=False, index=True)
    global_id = Column(String(50), ForeignKey('persons.global_id'), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    start_time = Column(DateTime, nullable=False)
    end_time = Column(DateTime, nullable=False)
    confidence = Column(Float, default=0.5)
    track_metadata = Column('metadata', JSON, default={})
    
    # Relationships
    person = relationship("Person", back_populates="tracks")
    camera = relationship("Camera", back_populates="tracks")
    observations = relationship("Observation", back_populates="track")
    
    def to_dict(self):
        return {
            'id': self.id,
            'track_id': self.track_id,
            'global_id': self.global_id,
            'camera_id': self.camera_id,
            'start_time': self.start_time.isoformat() if self.start_time else None,
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'confidence': self.confidence,
            'metadata': self.track_metadata or {}
        }

class Observation(Base):
    __tablename__ = 'observations'
    
    id = Column(Integer, primary_key=True)
    track_id = Column(String(50), ForeignKey('tracks.track_id'), nullable=False, index=True)
    global_id = Column(String(50), ForeignKey('persons.global_id'), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    bbox = Column(JSON, nullable=False)  # [x1, y1, x2, y2]
    confidence = Column(Float, default=0.5)
    quality = Column(Float, default=0.5)
    extra_metadata = Column('metadata', JSON, default={})
    
    # Relationships
    person = relationship("Person", back_populates="observations")
    camera = relationship("Camera", back_populates="observations")
    track = relationship("Track", back_populates="observations")
    
    __table_args__ = (
        Index('idx_observation_global_id_timestamp', 'global_id', 'timestamp'),
        Index('idx_observation_camera_id_timestamp', 'camera_id', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'track_id': self.track_id,
            'global_id': self.global_id,
            'camera_id': self.camera_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'bbox': self.bbox,
            'confidence': self.confidence,
            'quality': self.quality,
            'metadata': self.extra_metadata or {}
        }

class IdentityMatch(Base):
    __tablename__ = 'identity_matches'
    
    id = Column(Integer, primary_key=True)
    source_global_id = Column(String(50), nullable=False, index=True)
    target_global_id = Column(String(50), nullable=False, index=True)
    similarity = Column(Float, nullable=False)
    face_similarity = Column(Float, default=0.0)
    reid_similarity = Column(Float, default=0.0)
    matched_at = Column(DateTime, nullable=False)
    confidence = Column(Float, default=0.5)
    extra_metadata = Column('metadata', JSON, default={})
    
    __table_args__ = (
        Index('idx_identity_match_source_target', 'source_global_id', 'target_global_id'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'source_global_id': self.source_global_id,
            'target_global_id': self.target_global_id,
            'similarity': self.similarity,
            'face_similarity': self.face_similarity,
            'reid_similarity': self.reid_similarity,
            'matched_at': self.matched_at.isoformat() if self.matched_at else None,
            'confidence': self.confidence,
            'metadata': self.extra_metadata or {}
        }

class CameraTransition(Base):
    __tablename__ = 'camera_transitions'
    
    id = Column(Integer, primary_key=True)
    from_camera = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    to_camera = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    transition_probability = Column(Float, default=0.0)
    avg_travel_time = Column(Float, default=0.0)
    min_travel_time = Column(Float, default=0.0)
    max_travel_time = Column(Float, default=0.0)
    std_travel_time = Column(Float, default=0.0)
    observation_count = Column(Integer, default=0)
    last_observed = Column(DateTime, nullable=True)
    extra_metadata = Column('metadata', JSON, default={})
    
    __table_args__ = (
        Index('idx_camera_transition_from_to', 'from_camera', 'to_camera'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'from_camera': self.from_camera,
            'to_camera': self.to_camera,
            'transition_probability': self.transition_probability,
            'avg_travel_time': self.avg_travel_time,
            'min_travel_time': self.min_travel_time,
            'max_travel_time': self.max_travel_time,
            'std_travel_time': self.std_travel_time,
            'observation_count': self.observation_count,
            'last_observed': self.last_observed.isoformat() if self.last_observed else None,
            'metadata': self.extra_metadata or {}
        }

class Anomaly(Base):
    __tablename__ = 'anomalies'
    
    id = Column(Integer, primary_key=True)
    global_id = Column(String(50), ForeignKey('persons.global_id'), nullable=True, index=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'), nullable=True, index=True)
    anomaly_type = Column(String(50), nullable=False)
    severity = Column(String(20), nullable=False)  # critical, high, medium, low, info
    score = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    detected_at = Column(DateTime, nullable=False)
    resolved = Column(Boolean, default=False)
    resolved_at = Column(DateTime, nullable=True)
    extra_metadata = Column('metadata', JSON, default={})
    
    __table_args__ = (
        Index('idx_anomaly_global_id_detected', 'global_id', 'detected_at'),
        Index('idx_anomaly_camera_id_detected', 'camera_id', 'detected_at'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'global_id': self.global_id,
            'camera_id': self.camera_id,
            'anomaly_type': self.anomaly_type,
            'severity': self.severity,
            'score': self.score,
            'description': self.description,
            'detected_at': self.detected_at.isoformat() if self.detected_at else None,
            'resolved': self.resolved,
            'resolved_at': self.resolved_at.isoformat() if self.resolved_at else None,
            'metadata': self.extra_metadata or {}
        }

class CrowdMetric(Base):
    __tablename__ = 'crowd_metrics'
    
    id = Column(Integer, primary_key=True)
    camera_id = Column(Integer, ForeignKey('cameras.camera_id'), nullable=False, index=True)
    timestamp = Column(DateTime, nullable=False, index=True)
    occupancy = Column(Integer, nullable=False)
    capacity = Column(Integer, nullable=False)
    occupancy_percentage = Column(Float, nullable=False)
    entry_rate = Column(Float, default=0.0)
    exit_rate = Column(Float, default=0.0)
    dwell_time_avg = Column(Float, default=0.0)
    crowd_density = Column(Float, default=0.0)
    flow_rate = Column(Float, default=0.0)
    congestion_level = Column(String(20), nullable=False)
    extra_metadata = Column('metadata', JSON, default={})
    
    __table_args__ = (
        Index('idx_crowd_metric_camera_timestamp', 'camera_id', 'timestamp'),
    )
    
    def to_dict(self):
        return {
            'id': self.id,
            'camera_id': self.camera_id,
            'timestamp': self.timestamp.isoformat() if self.timestamp else None,
            'occupancy': self.occupancy,
            'capacity': self.capacity,
            'occupancy_percentage': self.occupancy_percentage,
            'entry_rate': self.entry_rate,
            'exit_rate': self.exit_rate,
            'dwell_time_avg': self.dwell_time_avg,
            'crowd_density': self.crowd_density,
            'flow_rate': self.flow_rate,
            'congestion_level': self.congestion_level,
            'metadata': self.extra_metadata or {}
        }