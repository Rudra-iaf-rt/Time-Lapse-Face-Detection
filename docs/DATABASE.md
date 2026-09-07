# Database

## SQLite (legacy)

- Module: `database/identity_store.py`
- File: `database/identities.db` (local; gitignored)
- Used by Streamlit, search index, topology learners

**Do not delete** when enabling PostgreSQL.

## PostgreSQL (server target)

- Models: `database/models.py`
- Manager: `database/postgres_manager.py`
- Pool: `database/connection_pool.py`
- Env: `POSTGRES_*`

## Qdrant

Face + Re-ID embeddings with payload metadata: `global_id`, `model_version`, `camera_id`, `timestamp`, `quality`.

## Redis

Short-lived track/camera/person cache and pub/sub for WebSocket fan-out. Not the identity system of record.
