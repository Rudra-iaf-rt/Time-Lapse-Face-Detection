# Multi-Camera Re-Identification System

AI-powered multi-camera person detection, tracking, and re-identification (Re-ID) platform for operator workflows. The system associates local camera tracks into a single canonical identity (`global_id`), supports cross-camera reappearance, and exposes results through a FastAPI backend, a React operator console, and a preserved Streamlit + SQLite dashboard.

**Version:** 3.0.0 (see `config.yaml`)  
**Canonical identity key:** `global_id` (for example `PERSON_DB5270AE` or `GID-00004`)  
**Local tracks:** camera-scoped identifiers (for example `CAM01-T17`)

---

## Overview

In multi-camera environments, the same person may appear under different local track IDs as they move between views. This project closes that gap by combining:

1. **Detection** — person localization (YOLOv8)
2. **Tracking** — per-camera temporal association
3. **Appearance Re-ID** — embedding-based matching across cameras (OSNet when weights are present; MobileNetV3 fallback for CPU demos)
4. **Optional face cues** — ArcFace-oriented face pipeline when model weights are available
5. **Fusion & topology** — multi-signal scoring plus spatial/temporal camera-graph constraints
6. **Operator interfaces** — live listing, search, timeline, analytics, and admin controls

The design keeps the original **Streamlit + SQLite IdentityStore** path fully usable while adding a modern **React → FastAPI → PostgreSQL / Qdrant / Redis** stack for production-oriented operations.

---

## Key Capabilities

| Area | Description |
|------|-------------|
| Multi-camera pipeline | Process synchronized or sequential video sources; emit crops, sightings, and identity state |
| Global identity management | Match or create identities; handle LOST / ACTIVE / resolved states |
| Cross-camera reappearance | Re-link a person who leaves one view and enters another |
| REST API | Persons, cameras, tracks, search, analytics, admin under `/api` and `/api/v1` |
| Authentication | JWT + bcrypt; roles `ADMIN`, `OPERATOR`, `VIEWER` |
| Real-time channel | WebSocket endpoint for subscriptions and live events |
| Vector search | Qdrant collections for Re-ID / face / appearance embeddings |
| Caching & pub/sub | Redis for person/track cache and event distribution |
| Operator UIs | React (primary) and Streamlit (legacy / offline-friendly) |
| Evaluation & edge | Metrics, latency benches, capability detection, optional FP16/ONNX paths |
| Ops tooling | Docker Compose, Postman/Newman collection, GitHub Actions CI, recovery scripts |

---

## Architecture

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  Video sources  │────▶│  pipeline.py     │────▶│  IdentityStore      │
│  cam01 / cam02  │     │  GlobalTracker   │     │  (SQLite)           │
└─────────────────┘     └──────────────────┘     └──────────┬──────────┘
                                                           │
                         optional sync                     │
                         scripts/sync_sqlite_to_postgres.py│
                                                           ▼
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  React frontend │────▶│  FastAPI         │────▶│  PostgreSQL         │
│  (Vite + TS)    │     │  /api, /api/v1   │     │  Qdrant · Redis     │
└─────────────────┘     └────────┬─────────┘     └─────────────────────┘
                                 │
                                 ▼
                        WebSocket / metrics
```

| Layer | Role |
|-------|------|
| **ML pipeline** | Detection, tracking, Re-ID embeddings, optional face fusion |
| **IdentityStore (SQLite)** | Authoritative store for Streamlit and primary list source for persons API |
| **PostgreSQL** | Relational store for API-oriented person records and timelines |
| **Qdrant** | Vector similarity for embeddings |
| **Redis** | Cache, TTLs, event publish/subscribe |
| **FastAPI** | Auth, REST, health probes, WebSocket, Prometheus `/metrics` |
| **React** | Operator console (dashboard, live, persons, timeline, search, cameras, topology, behavior, crowd, health, admin) |
| **Streamlit** | Legacy operator UI bound to SQLite |

Configuration is centralized in `config.yaml`. Connection settings for Postgres, Qdrant, and Redis can be overridden by environment variables (see `.env.example`).

---

## Technology Stack

| Component | Technology |
|-----------|------------|
| Language (backend / ML) | Python 3.10+ (verified with 3.12) |
| Detection | Ultralytics YOLOv8 |
| Re-ID | OSNet (weights optional) / MobileNetV3 fallback |
| Face (optional) | MTCNN + ArcFace weights |
| API | FastAPI, Uvicorn, Pydantic v2 |
| Auth | OAuth2 password form, JWT (`python-jose`), bcrypt |
| Databases | SQLite, PostgreSQL (asyncpg / SQLAlchemy), Qdrant, Redis |
| Frontend | React 19, TypeScript, Vite, Tailwind CSS, React Router |
| Legacy UI | Streamlit |
| Containers | Docker Compose (`docker/docker-compose.yml`) |
| Tests | Pytest, Vitest, Newman |

---

## Project Structure

```
multicam-reid/
├── api/                 # FastAPI application, routes, auth, middleware
├── websocket/           # Connection manager, event broadcaster, message handler
├── database/            # IdentityStore (SQLite), Postgres/Qdrant/Redis managers
├── tracker/             # Per-camera and global trackers
├── reid/                # Appearance embeddings, gallery, fusion helpers
├── face/                # Face detect / align / quality / embed
├── topology/            # Camera graph, spatial & temporal consistency
├── timeline/            # Event timelines and route analysis
├── search/              # Query engine and indexing
├── behavior/            # Behavior patterns and anomaly scoring
├── crowd/               # Occupancy, density, flow
├── dashboard/           # Streamlit operator UI
├── frontend/            # React operator console
├── eval/                # Evaluation metrics and benches
├── edge/                # Edge capability detection and metadata emission
├── docker/              # Compose stack for postgres, qdrant, redis
├── deployment/          # Prometheus / Grafana / recovery notes
├── postman/             # API collection for Newman
├── scripts/             # Model check, SQLite→PG sync, WebSocket E2E
├── videos/              # Sample inputs (cam01.mp4, cam02.mp4)
├── models/              # Place OSNet / ArcFace weights here
├── docs/                # Audit, status, and verification reports
├── pipeline.py          # End-to-end multi-camera runner
├── config.yaml          # Authoritative configuration
└── requirements*.txt    # Python dependencies
```

---

## Identity Model

- Use **`global_id` only** as the person key across APIs, UI, and storage bridges. Do not introduce a parallel `identity_id`.
- Local track IDs remain scoped to a single camera feed.
- Typical lifecycle: **new** → **active** → **lost** (after absence threshold) → **reappeared** (matched again) → optional **resolved**.

---

## Interfaces

| Interface | Persistence | Purpose |
|-----------|-------------|---------|
| **React** (`frontend/`) | FastAPI → PostgreSQL / Qdrant / Redis (+ IdentityStore reads) | Primary operator console |
| **Streamlit** (`dashboard/app.py`) | SQLite IdentityStore | Legacy / offline-friendly UI — must remain usable |
| **OpenAPI** | `http://127.0.0.1:8000/docs` | Interactive API reference |

### Health endpoints

| Path | Meaning |
|------|---------|
| `GET /live` | Process liveness |
| `GET /health` | Health summary |
| `GET /ready` | Ready only when PostgreSQL, Qdrant, and Redis report OK |
| `GET /metrics` | Prometheus metrics |

### Auth

- Login: `POST /api/auth/login` with **form** fields `username` and `password` (OAuth2 password flow).
- Default local credentials (override via `.env`): `admin` / `admin-change-me`.
- Roles: `ADMIN`, `OPERATOR`, `VIEWER`.

---

## Model Weights

| Model | Path | Notes |
|-------|------|--------|
| YOLOv8 | `yolov8n.pt` | May auto-download via Ultralytics on first run |
| OSNet | `models/osnet_x1_0_market_256x128.pth` | Required for full appearance Re-ID path |
| ArcFace | `models/arcface_r100_v1.pth` | Required for full face path |

Check status:

```bash
python scripts/download_models.py --check
```

Without OSNet/ArcFace weights, the sample pipeline still runs on CPU using **MobileNetV3** ImageNet features. Full production-grade Re-ID/face accuracy is blocked until weights are present. See `docs/IMPLEMENTATION_STATUS.md`.

---

## Configuration Notes

1. Copy `.env.example` to `.env` and set secrets before production use.
2. On many Windows hosts, a local PostgreSQL already occupies **5432**. This project’s Docker Postgres is published on **5433** by default (`POSTGRES_PORT=5433`).
3. For Docker Postgres with the sample compose password, run the API with `POSTGRES_PASSWORD=postgres` (or align `.env` with your compose file).
4. Frontend Vite variables: `VITE_API_BASE_URL`, `VITE_WS_URL` (see `frontend/.env.example` if present, or root `.env.example`).

---

## Documentation

| Document | Contents |
|----------|----------|
| `docs/ARCHITECTURE_AUDIT.md` | Repository audit baseline |
| `docs/IMPLEMENTATION_STATUS.md` | Evidence-based feature status |
| `docs/FINAL_VERIFICATION_REPORT.md` | Verification results (do not assume 100% complete) |
| `postman/README.md` | Collection usage |
| `eval/README.md` | Evaluation notes |
| `edge/README.md` | Edge deployment notes |

---

## Testing

```bash
# Backend unit / smoke
pytest tests/test_api_unit.py tests/test_eval_edge.py tests/test_streamlit_smoke.py -q

# Frontend
cd frontend
npm test
npm run build

# API collection (API must be running)
npx newman run postman/Multicam_ReID.postman_collection.json -e postman/Multicam_ReID.postman_environment.json
```

WebSocket connectivity smoke test:

```bash
python scripts/ws_e2e_test.py
```

---

## Current Status (summary)

The platform is **partially implemented** toward a full production multi-camera Re-ID product:

- **Working:** API health stack, JWT auth, React build, Docker infra, sample multi-camera pipeline (MobileNet path), SQLite IdentityStore, optional Postgres sync, Postman/Newman, unit/smoke tests.
- **Blocked / incomplete:** OSNet and ArcFace weight files for the full ML accuracy path; deep WebSocket event fan-out should be treated as partially verified.

Always prefer `docs/FINAL_VERIFICATION_REPORT.md` over informal “complete” claims.

---

## How to Run

Commands below assume you are in the project root:

`c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid`

Use separate VS Code / Cursor terminal tabs for Docker (one-shot), API, pipeline, and frontend.

### Prerequisites

- Python 3.10+ with `pip`
- Node.js 18+ and `npm`
- Docker Desktop running
- (Recommended) Git

### Step 1 — Enter the project

**PowerShell**

```powershell
cd "c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid"
```

**bash**

```bash
cd "/path/to/multicam-reid"
```

### Step 2 — Python dependencies

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
pip install -r requirements-dev.txt
```

Install PyTorch for your platform first if needed (CPU or CUDA wheels from the official PyTorch site).

### Step 3 — Environment file

```powershell
Copy-Item .env.example .env
```

Edit `.env` as needed. For local Docker Postgres matching compose defaults, set:

```text
POSTGRES_PORT=5433
POSTGRES_PASSWORD=postgres
```

### Step 4 — Start infrastructure

```powershell
docker compose -f docker/docker-compose.yml up -d postgres qdrant redis
```

Confirm containers are healthy in Docker Desktop or with `docker compose -f docker/docker-compose.yml ps`.

### Step 5 — Start the API

```powershell
cd "c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid"
$env:POSTGRES_PORT = "5433"
$env:POSTGRES_PASSWORD = "postgres"
uvicorn api.main:app --host 127.0.0.1 --port 8000 --reload
```

Verify readiness:

```powershell
Invoke-RestMethod http://127.0.0.1:8000/ready
```

Open interactive docs: [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs)

Login (form body):

```powershell
Invoke-RestMethod -Uri http://127.0.0.1:8000/api/auth/login -Method Post -Body @{
  username = "admin"
  password = "admin-change-me"
}
```

### Step 6 — Run the sample multi-camera pipeline

In a **new** terminal (with the same venv activated):

```powershell
cd "c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid"
python pipeline.py --videos videos/cam01.mp4 videos/cam02.mp4 --output results/e2e_run --device cpu --no-video
```

Outputs:

- Identities and sightings → `database/identities.db`
- Crops / run artifacts → `results/e2e_run/`

Optional bridge into PostgreSQL:

```powershell
python scripts/sync_sqlite_to_postgres.py
```

### Step 7 — Start the React operator UI

In a **new** terminal:

```powershell
cd "c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid\frontend"
npm install
npm run dev
```

Open the URL printed by Vite (typically [http://127.0.0.1:5173](http://127.0.0.1:5173)).

Sign in with `admin` / `admin-change-me` unless you changed `.env`.

### Step 8 — (Optional) Streamlit dashboard

```powershell
cd "c:\Users\G Rudra\OneDrive\Desktop\Face Detection\multicam-reid"
streamlit run dashboard/app.py
```

### Step 9 — (Optional) Model weight check

```powershell
python scripts/download_models.py --check
```

---

## License and Contribution

Use and extend this repository according to your organization’s internal policy. Prefer small, reviewable changes; keep Streamlit + SQLite behavior intact when modifying the API path; and never commit real secrets or large model weight binaries unless explicitly agreed.
