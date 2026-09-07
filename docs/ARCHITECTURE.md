# Architecture

```text
MULTIPLE CAMERAS
      │
      ▼
Detection + Tracking
      │
      ▼
Face + Re-ID
      │
      ▼
Identity Fusion → global_id
      │
      ├─ Timeline / Behavior / Analytics
      ▼
Service Layer → FastAPI
      ├─ PostgreSQL
      ├─ Qdrant
      └─ Redis
      ▼
React Dashboard (+ WebSocket)
```

Legacy path:

```text
Streamlit → SQLite IdentityStore
```

Shared business logic should live in Python services (`database/`, `search/`, `topology/`, …), not duplicated in React.
