# database/qdrant_manager.py
import numpy as np
from typing import Dict, List, Optional
from datetime import datetime
import uuid
import logging
from qdrant_client import QdrantClient
from qdrant_client.models import (
    Distance,
    VectorParams,
    PointStruct,
    Filter,
    FieldCondition,
    MatchValue,
    PointIdsList,
    FilterSelector,
)

logger = logging.getLogger(__name__)


def _point_uuid(seed: str) -> str:
    """Qdrant point IDs must be UUID or unsigned int."""
    return str(uuid.uuid5(uuid.NAMESPACE_URL, seed))


class QdrantManager:
    """Qdrant vector database manager for face and Re-ID embeddings."""

    def __init__(self, config: dict):
        self.config = config
        self.qdrant_config = config.get("qdrant", {})
        self.host = self.qdrant_config.get("host", "localhost")
        self.port = self.qdrant_config.get("port", 6333)
        self.vector_size = self.qdrant_config.get("vector_size", 512)
        self.distance = self.qdrant_config.get("distance", "Cosine")
        self.collections = {
            "face_embeddings": self.qdrant_config.get("face_collection", "face_embeddings"),
            "reid_embeddings": self.qdrant_config.get("reid_collection", "reid_embeddings"),
            "appearance_embeddings": self.qdrant_config.get(
                "appearance_collection", "appearance_embeddings"
            ),
        }
        self.client = None
        self._initialized = False

    def initialize(self):
        if self._initialized:
            return
        try:
            self.client = QdrantClient(host=self.host, port=self.port, timeout=30, check_compatibility=False)
            for collection_name in self.collections.values():
                self._create_collection(collection_name)
            self._initialized = True
            logger.info("Qdrant connected to %s:%s", self.host, self.port)
        except Exception as e:
            logger.error("Failed to connect to Qdrant: %s", e)
            raise

    def health_check(self) -> bool:
        if not self._initialized:
            self.initialize()
        self.client.get_collections()
        return True

    def _create_collection(self, collection_name: str):
        collections = self.client.get_collections().collections
        names = [c.name for c in collections]
        if collection_name not in names:
            self.client.create_collection(
                collection_name=collection_name,
                vectors_config=VectorParams(
                    size=self.vector_size,
                    distance=Distance[self.distance.upper()],
                ),
            )
            logger.info("Created Qdrant collection: %s", collection_name)

    def upsert_embedding(
        self,
        collection_name: str,
        point_id: str,
        embedding: np.ndarray,
        metadata: Dict,
    ) -> bool:
        if not self._initialized:
            self.initialize()
        vec = np.asarray(embedding, dtype=np.float32).reshape(-1)
        if vec.shape[0] != self.vector_size:
            raise ValueError(f"Embedding shape {vec.shape} != ({self.vector_size},)")
        payload = dict(metadata or {})
        point = PointStruct(id=point_id, vector=vec.tolist(), payload=payload)
        self.client.upsert(collection_name=collection_name, points=[point])
        return True

    def search_embeddings(
        self,
        collection_name: str,
        query_embedding: np.ndarray,
        limit: int = 10,
        score_threshold: float = 0.0,
        metadata_filter: Optional[Dict] = None,
    ) -> List[Dict]:
        if not self._initialized:
            self.initialize()
        vec = np.asarray(query_embedding, dtype=np.float32).reshape(-1)
        if vec.shape[0] != self.vector_size:
            raise ValueError(f"Embedding shape {vec.shape} != ({self.vector_size},)")

        search_filter = None
        if metadata_filter:
            conditions = [
                FieldCondition(key=key, match=MatchValue(value=value))
                for key, value in metadata_filter.items()
            ]
            if conditions:
                search_filter = Filter(must=conditions)

        results = self.client.search(
            collection_name=collection_name,
            query_vector=vec.tolist(),
            limit=limit,
            score_threshold=score_threshold,
            query_filter=search_filter,
            with_payload=True,
            with_vectors=False,
        )
        return [{"id": r.id, "score": r.score, "payload": r.payload} for r in results]

    def delete_embedding(self, collection_name: str, point_id: str) -> bool:
        if not self._initialized:
            self.initialize()
        self.client.delete(
            collection_name=collection_name,
            points_selector=PointIdsList(points=[point_id]),
        )
        return True

    def delete_embeddings_for_person(self, global_id: str) -> bool:
        if not self._initialized:
            self.initialize()
        for collection_name in self.collections.values():
            self.client.delete(
                collection_name=collection_name,
                points_selector=FilterSelector(
                    filter=Filter(
                        must=[
                            FieldCondition(
                                key="global_id", match=MatchValue(value=global_id)
                            )
                        ]
                    )
                ),
            )
        return True

    def get_collection_stats(self, collection_name: str) -> Dict:
        if not self._initialized:
            self.initialize()
        info = self.client.get_collection(collection_name)
        return {
            "name": collection_name,
            "status": str(info.status),
            "points_count": getattr(info, "points_count", None),
            "vectors_count": getattr(info, "vectors_count", None),
        }

    def upsert_face_embedding(
        self, global_id: str, face_embedding: np.ndarray, metadata: Dict
    ) -> bool:
        point_id = _point_uuid(f"face:{global_id}:{metadata.get('timestamp', 'latest')}")
        meta = dict(metadata)
        meta["global_id"] = global_id
        meta["type"] = "face"
        meta.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
        return self.upsert_embedding(
            self.collections["face_embeddings"], point_id, face_embedding, meta
        )

    def upsert_reid_embedding(
        self, global_id: str, reid_embedding: np.ndarray, metadata: Dict
    ) -> bool:
        point_id = _point_uuid(f"reid:{global_id}:{metadata.get('timestamp', 'latest')}")
        meta = dict(metadata)
        meta["global_id"] = global_id
        meta["type"] = "reid"
        meta.setdefault("timestamp", datetime.utcnow().isoformat() + "Z")
        return self.upsert_embedding(
            self.collections["reid_embeddings"], point_id, reid_embedding, meta
        )

    def search_face_embeddings(
        self,
        query_embedding: np.ndarray,
        global_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.6,
    ) -> List[Dict]:
        metadata_filter = {"global_id": global_id} if global_id else None
        return self.search_embeddings(
            self.collections["face_embeddings"],
            query_embedding,
            limit=limit,
            score_threshold=threshold,
            metadata_filter=metadata_filter,
        )

    def search_reid_embeddings(
        self,
        query_embedding: np.ndarray,
        global_id: Optional[str] = None,
        limit: int = 10,
        threshold: float = 0.5,
    ) -> List[Dict]:
        metadata_filter = {"global_id": global_id} if global_id else None
        return self.search_embeddings(
            self.collections["reid_embeddings"],
            query_embedding,
            limit=limit,
            score_threshold=threshold,
            metadata_filter=metadata_filter,
        )
