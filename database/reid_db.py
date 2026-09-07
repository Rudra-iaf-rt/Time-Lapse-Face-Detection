# database/reid_db.py
"""
Re-ID profile helpers bridging SQLite IdentityStore and PostgreSQL/Qdrant.

SQLite remains the Streamlit/legacy store. This module does not delete or migrate
SQLite automatically.
"""

from __future__ import annotations

import logging
from typing import Any, Dict, List, Optional

import numpy as np

from database.identity_store import IdentityStore
from database.postgres_manager import PostgresManager
from database.qdrant_manager import QdrantManager

logger = logging.getLogger(__name__)


class ReidDB:
    """Facade for identity + embedding operations using global_id only."""

    def __init__(
        self,
        identity_store: IdentityStore,
        postgres: Optional[PostgresManager] = None,
        qdrant: Optional[QdrantManager] = None,
    ):
        self.store = identity_store
        self.postgres = postgres
        self.qdrant = qdrant

    def get_person(self, global_id: str) -> Optional[Dict[str, Any]]:
        return self.store.get_person(global_id)

    def list_persons(self, limit: int = 100, offset: int = 0) -> List[Dict[str, Any]]:
        all_rows = self.store.get_all()
        return all_rows[offset : offset + limit]

    def add_note(self, global_id: str, note: str) -> bool:
        return self.store.add_note(global_id, note)

    def resolve(self, global_id: str) -> bool:
        return self.store.resolve(global_id)

    def reactivate(self, global_id: str) -> bool:
        return self.store.reactivate(global_id)

    def upsert_reid_embedding(
        self,
        global_id: str,
        embedding: np.ndarray,
        *,
        camera_id: Optional[str] = None,
        model_version: str = "osnet_x1_0",
        quality: float = 0.0,
        timestamp: Optional[str] = None,
    ) -> bool:
        if self.qdrant is None:
            raise RuntimeError("Qdrant manager is not available")
        metadata = {
            "global_id": global_id,
            "model_version": model_version,
            "quality": quality,
        }
        if camera_id is not None:
            metadata["camera_id"] = camera_id
        if timestamp is not None:
            metadata["timestamp"] = timestamp
        return self.qdrant.upsert_reid_embedding(global_id, embedding, metadata)

    def upsert_face_embedding(
        self,
        global_id: str,
        embedding: np.ndarray,
        *,
        camera_id: Optional[str] = None,
        model_version: str = "arcface",
        quality: float = 0.0,
        timestamp: Optional[str] = None,
    ) -> bool:
        if self.qdrant is None:
            raise RuntimeError("Qdrant manager is not available")
        metadata = {
            "global_id": global_id,
            "model_version": model_version,
            "quality": quality,
        }
        if camera_id is not None:
            metadata["camera_id"] = camera_id
        if timestamp is not None:
            metadata["timestamp"] = timestamp
        return self.qdrant.upsert_face_embedding(global_id, embedding, metadata)

    def search_similar_reid(
        self, embedding: np.ndarray, limit: int = 10, threshold: float = 0.5
    ) -> List[Dict]:
        if self.qdrant is None:
            raise RuntimeError("Qdrant manager is not available")
        return self.qdrant.search_reid_embeddings(embedding, limit=limit, threshold=threshold)
