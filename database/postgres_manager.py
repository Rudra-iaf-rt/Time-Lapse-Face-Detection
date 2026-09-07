# database/postgres_manager.py
import asyncio
from typing import Dict, List, Optional, Any, Union
from datetime import datetime
import asyncpg
import sqlalchemy as sa
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession
from sqlalchemy.orm import sessionmaker, declarative_base
from sqlalchemy import Column, Integer, String, Float, DateTime, Text, Boolean, JSON, ForeignKey
from contextlib import asynccontextmanager
import json
import logging

from .models import Base, Person, BiometricProfile, Camera, Track, Observation, IdentityMatch

logger = logging.getLogger(__name__)

class PostgresManager:
    """
    PostgreSQL database manager with async support.
    """
    
    def __init__(self, config: dict):
        self.config = config
        self.db_config = config.get('postgres', {})
        
        # Connection parameters
        self.host = self.db_config.get('host', 'localhost')
        self.port = self.db_config.get('port', 5432)
        self.database = self.db_config.get('database', 'multicam_reid')
        self.user = self.db_config.get('user', 'postgres')
        self.password = self.db_config.get('password', 'postgres')
        self.pool_size = self.db_config.get('pool_size', 10)
        self.max_overflow = self.db_config.get('max_overflow', 20)
        
        # Create connection string
        self.dsn = f"postgresql://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        self.async_dsn = f"postgresql+asyncpg://{self.user}:{self.password}@{self.host}:{self.port}/{self.database}"
        
        # Initialize engine and session
        self.engine = None
        self.async_session = None
        self._initialized = False
        
    async def initialize(self):
        """Initialize database connection."""
        if self._initialized:
            return
        
        try:
            # Create async engine
            self.engine = create_async_engine(
                self.async_dsn,
                echo=self.config.get('debug', False),
                pool_size=self.pool_size,
                max_overflow=self.max_overflow,
                pool_pre_ping=True,
                pool_recycle=3600
            )
            
            # Create async session
            self.async_session = sessionmaker(
                self.engine,
                class_=AsyncSession,
                expire_on_commit=False
            )
            
            # Create tables if they don't exist
            async with self.engine.begin() as conn:
                await conn.run_sync(Base.metadata.create_all)
            
            self._initialized = True
            logger.info(f"OK: PostgreSQL connected to {self.host}:{self.port}/{self.database}")
            
        except Exception as e:
            logger.error(f"ERROR: Failed to connect to PostgreSQL: {e}")
            raise
    
    @asynccontextmanager
    async def get_session(self):
        """Get a database session."""
        if not self._initialized:
            await self.initialize()
        
        async with self.async_session() as session:
            try:
                yield session
                await session.commit()
            except Exception:
                await session.rollback()
                raise
            finally:
                await session.close()
    
    # Person Operations
    async def create_person(self, person_data: Dict) -> Dict:
        """Create a new person record."""
        async with self.get_session() as session:
            person = Person(
                global_id=person_data['global_id'],
                first_seen=person_data.get('first_seen', datetime.now()),
                last_seen=person_data.get('last_seen', datetime.now()),
                confidence=person_data.get('confidence', 0.5),
                person_metadata=person_data.get('metadata', {})
            )
            session.add(person)
            await session.flush()
            return person.to_dict()
    
    async def get_person(self, global_id: str) -> Optional[Dict]:
        """Get a person by global ID."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(Person).where(Person.global_id == global_id)
            )
            person = result.scalar_one_or_none()
            return person.to_dict() if person else None
    
    async def update_person(self, global_id: str, updates: Dict) -> Optional[Dict]:
        """Update a person record."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(Person).where(Person.global_id == global_id)
            )
            person = result.scalar_one_or_none()
            if not person:
                return None
            
            for key, value in updates.items():
                if key == 'metadata':
                    person.person_metadata = value
                elif hasattr(person, key):
                    setattr(person, key, value)
            
            person.last_seen = datetime.now()
            await session.flush()
            return person.to_dict()
    
    # Biometric Profile Operations
    async def create_biometric_profile(self, profile_data: Dict) -> Dict:
        """Create a biometric profile."""
        async with self.get_session() as session:
            profile = BiometricProfile(
                global_id=profile_data['global_id'],
                face_embedding=profile_data.get('face_embedding'),
                reid_embedding=profile_data.get('reid_embedding'),
                appearance_embedding=profile_data.get('appearance_embedding'),
                face_quality=profile_data.get('face_quality', 0.0),
                reid_quality=profile_data.get('reid_quality', 0.0),
                created_at=datetime.now(),
                updated_at=datetime.now()
            )
            session.add(profile)
            await session.flush()
            return profile.to_dict()
    
    async def get_biometric_profile(self, global_id: str) -> Optional[Dict]:
        """Get a biometric profile."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(BiometricProfile).where(BiometricProfile.global_id == global_id)
            )
            profile = result.scalar_one_or_none()
            return profile.to_dict() if profile else None
    
    async def update_biometric_profile(self, global_id: str, updates: Dict) -> Optional[Dict]:
        """Update a biometric profile."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(BiometricProfile).where(BiometricProfile.global_id == global_id)
            )
            profile = result.scalar_one_or_none()
            if not profile:
                return None
            
            for key, value in updates.items():
                if hasattr(profile, key):
                    setattr(profile, key, value)
            
            profile.updated_at = datetime.now()
            await session.flush()
            return profile.to_dict()
    
    # Camera Operations
    async def create_camera(self, camera_data: Dict) -> Dict:
        """Create a camera record."""
        async with self.get_session() as session:
            camera = Camera(
                camera_id=camera_data['camera_id'],
                name=camera_data.get('name', f"Camera_{camera_data['camera_id']}"),
                location=camera_data.get('location'),
                capacity=camera_data.get('capacity', 100),
                camera_metadata=camera_data.get('metadata', {})
            )
            session.add(camera)
            await session.flush()
            return camera.to_dict()
    
    async def get_camera(self, camera_id: int) -> Optional[Dict]:
        """Get a camera by ID."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(Camera).where(Camera.camera_id == camera_id)
            )
            camera = result.scalar_one_or_none()
            return camera.to_dict() if camera else None
    
    async def get_all_cameras(self) -> List[Dict]:
        """Get all cameras."""
        async with self.get_session() as session:
            result = await session.execute(sa.select(Camera))
            cameras = result.scalars().all()
            return [c.to_dict() for c in cameras]
    
    # Track Operations
    async def create_track(self, track_data: Dict) -> Dict:
        """Create a track record."""
        async with self.get_session() as session:
            track = Track(
                track_id=track_data['track_id'],
                global_id=track_data.get('global_id'),
                camera_id=track_data['camera_id'],
                start_time=track_data.get('start_time', datetime.now()),
                end_time=track_data.get('end_time', datetime.now()),
                confidence=track_data.get('confidence', 0.5),
                track_metadata=track_data.get('metadata', {})
            )
            session.add(track)
            await session.flush()
            return track.to_dict()
    
    async def get_tracks_by_person(self, global_id: str) -> List[Dict]:
        """Get all tracks for a person."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(Track).where(Track.global_id == global_id)
            )
            tracks = result.scalars().all()
            return [t.to_dict() for t in tracks]
    
    # Observation Operations
    async def create_observation(self, observation_data: Dict) -> Dict:
        """Create an observation record."""
        async with self.get_session() as session:
            observation = Observation(
                track_id=observation_data['track_id'],
                global_id=observation_data.get('global_id'),
                camera_id=observation_data['camera_id'],
                timestamp=observation_data.get('timestamp', datetime.now()),
                bbox=observation_data.get('bbox', [0, 0, 100, 100]),
                confidence=observation_data.get('confidence', 0.5),
                quality=observation_data.get('quality', 0.5),
                extra_metadata=observation_data.get('metadata', {})
            )
            session.add(observation)
            await session.flush()
            return observation.to_dict()
    
    async def get_observations(self, global_id: str, 
                               start_time: Optional[datetime] = None,
                               end_time: Optional[datetime] = None) -> List[Dict]:
        """Get observations for a person in a time range."""
        async with self.get_session() as session:
            query = sa.select(Observation).where(Observation.global_id == global_id)
            
            if start_time:
                query = query.where(Observation.timestamp >= start_time)
            if end_time:
                query = query.where(Observation.timestamp <= end_time)
            
            query = query.order_by(Observation.timestamp)
            
            result = await session.execute(query)
            observations = result.scalars().all()
            return [o.to_dict() for o in observations]
    
    # Identity Match Operations
    async def create_identity_match(self, match_data: Dict) -> Dict:
        """Create an identity match record."""
        async with self.get_session() as session:
            match = IdentityMatch(
                source_global_id=match_data['source_global_id'],
                target_global_id=match_data['target_global_id'],
                similarity=match_data['similarity'],
                face_similarity=match_data.get('face_similarity', 0.0),
                reid_similarity=match_data.get('reid_similarity', 0.0),
                matched_at=datetime.now(),
                confidence=match_data.get('confidence', 0.5),
                extra_metadata=match_data.get('metadata', {})
            )
            session.add(match)
            await session.flush()
            return match.to_dict()
    
    async def get_identity_matches(self, global_id: str) -> List[Dict]:
        """Get all identity matches for a person."""
        async with self.get_session() as session:
            result = await session.execute(
                sa.select(IdentityMatch).where(
                    (IdentityMatch.source_global_id == global_id) |
                    (IdentityMatch.target_global_id == global_id)
                )
            )
            matches = result.scalars().all()
            return [m.to_dict() for m in matches]
    
    # Analytics Operations
    async def get_camera_statistics(self, camera_id: int, 
                                   start_time: datetime,
                                   end_time: datetime) -> Dict:
        """Get camera statistics for a time range."""
        async with self.get_session() as session:
            # Count observations
            result = await session.execute(
                sa.select(sa.func.count(Observation.id))
                .where(Observation.camera_id == camera_id)
                .where(Observation.timestamp >= start_time)
                .where(Observation.timestamp <= end_time)
            )
            observation_count = result.scalar()
            
            # Count unique persons
            result = await session.execute(
                sa.select(sa.func.count(sa.distinct(Observation.global_id)))
                .where(Observation.camera_id == camera_id)
                .where(Observation.timestamp >= start_time)
                .where(Observation.timestamp <= end_time)
            )
            unique_persons = result.scalar()
            
            # Average confidence
            result = await session.execute(
                sa.select(sa.func.avg(Observation.confidence))
                .where(Observation.camera_id == camera_id)
                .where(Observation.timestamp >= start_time)
                .where(Observation.timestamp <= end_time)
            )
            avg_confidence = result.scalar() or 0.0
            
            return {
                'camera_id': camera_id,
                'observation_count': observation_count,
                'unique_persons': unique_persons,
                'avg_confidence': float(avg_confidence),
                'start_time': start_time.isoformat(),
                'end_time': end_time.isoformat()
            }
    
    async def get_person_timeline(self, global_id: str) -> Dict:
        """Get a person's complete timeline."""
        observations = await self.get_observations(global_id)
        
        if not observations:
            return {
                'global_id': global_id,
                'events': [],
                'cameras_visited': [],
                'total_duration': 0
            }
        
        # Build timeline (to_dict() already ISO-formats timestamps)
        events = []
        parsed_times = []
        for obs in observations:
            ts = obs['timestamp']
            if isinstance(ts, datetime):
                ts_str = ts.isoformat()
                parsed_times.append(ts)
            else:
                ts_str = ts
                try:
                    parsed_times.append(datetime.fromisoformat(str(ts).replace('Z', '')))
                except (TypeError, ValueError):
                    pass
            events.append({
                'timestamp': ts_str,
                'camera_id': obs['camera_id'],
                'bbox': obs['bbox'],
                'confidence': obs['confidence']
            })
        
        cameras_visited = list(set([o['camera_id'] for o in observations]))
        
        # Calculate total duration
        if len(parsed_times) >= 2:
            total_duration = (max(parsed_times) - min(parsed_times)).total_seconds()
        else:
            total_duration = 0
        
        return {
            'global_id': global_id,
            'events': events,
            'cameras_visited': cameras_visited,
            'total_duration': total_duration
        }
    
    async def close(self):
        """Close database connections."""
        if self.engine:
            await self.engine.dispose()
            logger.info("OK: PostgreSQL connections closed")