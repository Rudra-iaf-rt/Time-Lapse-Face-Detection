# Architecture Audit

**Date:** 2026-09-08  
**Repository:** `multicam-reid/`  
**Rule:** Status derived only from repository contents. No invented completion percentages.

---

## 1. Summary

| Area | Evidence-based status |
|------|------------------------|
| ML pipeline (detect / track / Re-ID / face / fusion) | Substantial Python present |
| Streamlit + SQLite IdentityStore | Present and used by `dashboard/app.py` |
| FastAPI | `api/main.py` present but **cannot start** (empty dependency modules) |
| PostgreSQL / Qdrant / Redis managers | Non-empty manager modules present |
| React frontend | **Not present** (`frontend/` missing) |
| Evaluation framework | `eval/` exists with **empty** stubs only |
| Edge / deployment / Postman / CI | **Not present** |
| Docker Compose | File present; **empty** mount configs for postgres/qdrant/redis |

---

## 2. Directory inventory (source of truth)

### Present with substantial code

- `face/` — detector, aligner, quality, embedder, gallery
- `tracker/` — `enhanced_tracker.py`, `global_tracker.py`
- `reid/` — OSNet, gallery, quality, multimodal fusion, feature extractor
- `topology/` — camera graph, spatial/temporal consistency, transition learner
- `timeline/` — builder, aggregator, event detector, route analyzer, storage
- `search/` — query engine, builder, index, filters, aggregators
- `behavior/` — analyzer, anomaly detector/scorer, rules, patterns, storage
- `crowd/` — occupancy, density, flow, predictor, storage
- `dashboard/app.py` — Streamlit operator UI (real)
- `database/identity_store.py` — SQLite (~42KB), used by Streamlit
- `database/models.py`, `postgres_manager.py`, `qdrant_manager.py`, `redis_manager.py`
- `pipeline.py`, `run_reid.py`
- `videos/cam01.mp4`, `videos/cam02.mp4`
- Partial API: `api/main.py`, `routes/persons.py`, `routes/search.py`, `routes/websocket.py`
- Partial schemas: `person.py`, `camera.py`, `search.py`
- Partial websocket: `connection_manager.py`, `event_broadcaster.py`
- Tests for earlier phases under `tests/`

### Present but empty (0 bytes) — API startup blockers

| Path | Bytes |
|------|------:|
| `api/__init__.py` | 0 |
| `api/dependencies/auth.py` | 0 |
| `api/dependencies/database.py` | 0 |
| `api/dependencies/__init__.py` | 0 |
| `api/middleware/auth.py` | 0 |
| `api/middleware/cors.py` | 0 |
| `api/middleware/logging.py` | 0 |
| `api/middleware/__init__.py` | 0 |
| `api/routes/admin.py` | 0 |
| `api/routes/analytics.py` | 0 |
| `api/routes/cameras.py` | 0 |
| `api/routes/tracks.py` | 0 |
| `api/routes/__init__.py` | 0 |
| `api/schemas/response.py` | 0 |
| `api/schemas/track.py` | 0 |
| `api/schemas/__init__.py` | 0 |
| `database/connection_pool.py` | 0 |
| `database/migrations.py` | 0 |
| `database/reid_db.py` | 0 |
| `database/__init__.py` | 0 |
| `websocket/message_handler.py` | 0 |
| `websocket/__init__.py` | 0 |
| `docker/postgres/init.sql` | 0 |
| `docker/qdrant/config.yaml` | 0 |
| `docker/redis/redis.conf` | 0 |
| `eval/__init__.py` | 0 |
| `eval/reid_evaluator.py` | 0 |

### Missing directories / stacks

- `frontend/` — no React app
- `edge/` — not present
- `deployment/` — not present
- `postman/` — not present
- `docs/` — was missing at audit start (created for this document)
- `.github/workflows/` — not present
- Root `.env.example` — not present

---

## 3. Import / dependency map (FastAPI)

`api/main.py` imports:

```
api.routes: persons, cameras, tracks, search, analytics, websocket, admin
api.middleware: auth, cors, logging
api.dependencies.database: init_db, close_db
api.schemas.response: ResponseModel, ErrorResponse
```

**Startup blockers:**

1. Empty modules listed above → `ImportError` / empty module attribute errors.
2. `api/main.py` uses `datetime` without importing it.
3. `api/routes/persons.py` uses `get_qdrant_manager` / `get_redis_manager` without defining/importing them (and those deps live in empty `database.py`).
4. `list_persons` returns hardcoded empty list (stub).
5. Search route passes a Pydantic `.dict()` into `QueryEngine.search()`, which expects the `search.query_builder.SearchQuery` object — type mismatch.

---

## 4. SQLite vs PostgreSQL split

| Store | Path / module | Consumers |
|-------|---------------|-----------|
| SQLite | `database/identities.db` via `IdentityStore` | Streamlit dashboard, search index, topology, timeline, behavior, crowd (legacy path) |
| PostgreSQL | `PostgresManager` + SQLAlchemy `models.py` | Intended FastAPI persistence (not wired until deps implemented) |
| Qdrant | `QdrantManager` | Vector face/Re-ID embeddings (intended) |
| Redis | `RedisManager` | Short-lived track/camera/WS cache (intended) |

**Rule going forward:** Keep `identity_store.py` + SQLite for Streamlit. PostgreSQL is the target server-side store for FastAPI/React. Do not delete SQLite data.

---

## 5. Configuration inconsistencies

`config.yaml` issues observed:

- **Duplicate `fusion:` blocks** (first ~lines 38–53, second ~lines 74–89). YAML parsers keep the **last** block only.
- Hardcoded `postgres.password: postgres` in config (dev default; must move to env for production).
- Trailing comment `# ... rest of config` (noise).
- `reid.device: "cuda"` — may fail on CPU-only machines unless overridden.
- Model paths: `models/osnet_x1_0_market_256x128.pth`, `models/arcface_r100_v1.pth` — weight **files not present** under `models/` (only empty-ish dirs `arcface/`, `face_detection/`).

`requirements.txt` issues:

- Duplicate / conflicting version pins (`torch`, `numpy`, `pydantic` 1.x and 2.x ranges).
- Invalid / non-pip packages: `pgbouncer`, `asyncio` (stdlib).
- Noisy merge residue from multiple phase appends.

---

## 6. Hardcoded secrets

| Location | Finding |
|----------|---------|
| `config.yaml` | `postgres.password: postgres` |
| `docker/docker-compose.yml` | `POSTGRES_PASSWORD: postgres`, pgAdmin `admin`/`admin` |
| Source code | No JWT secret module yet (empty auth files) |

---

## 7. Model weights

- Config references OSNet and ArcFace `.pth` paths.
- `models/` contains directories only; no weight files found with non-zero size at audit time.
- Application should fail with a clear “run download command” message (to be implemented), not an obscure stack trace.

---

## 8. Docker

`docker/docker-compose.yml` defines: postgres, qdrant, redis, pgadmin, redis-commander.

Problems:

- Mounts empty `init.sql`, `qdrant/config.yaml`, `redis/redis.conf` → Redis may fail if conf is empty; Qdrant mount of empty yaml is risky.
- No `api` or `frontend` services.
- Dev tools (pgadmin, redis-commander) always on (should be optional profile).
- `Dockerfile/dockerfile` exists (567 bytes) — incomplete production image wiring.

---

## 9. WebSocket

| File | Status |
|------|--------|
| `connection_manager.py` | Implemented |
| `event_broadcaster.py` | Implemented (Redis pub/sub) |
| `message_handler.py` | **Empty** — imported by `api/routes/websocket.py` |

---

## 10. Tests

Present: `test_api.py` (live HTTP against localhost:8000 — integration-style, not pytest fixtures), plus ML/phase tests (`test_face`, `test_topology`, `test_search`, `test_behavior`, `test_crowd`, etc.).

`test_api.py` assumes a running server; it will fail until FastAPI starts.

---

## 11. Identity model

Canonical key in IdentityStore and SQLAlchemy models: **`global_id`**.

Local tracks use camera-scoped track IDs (e.g. `CAM01-T17`).  
No `identity_id` alternate key should be introduced.

---

## 12. Dual-interface target

```
Legacy:  Streamlit → SQLite IdentityStore   (KEEP)
Target:  ML → Services → FastAPI → Postgres/Qdrant/Redis → React
```

React must not duplicate business logic; Streamlit must remain runnable.

---

## 13. Immediate repair priority (Phase 9)

1. Fill empty API middleware / dependencies / schemas / routes.
2. Fix `api/main.py` imports and `/health` `/live` `/ready`.
3. Wire Postgres / Qdrant / Redis lifecycle + health probes.
4. Implement JWT auth + WebSocket message handler.
5. Run import/startup verification before any React work.

---

*End of audit. Claims in this document map to file presence and byte sizes observed on 2026-09-08.*
