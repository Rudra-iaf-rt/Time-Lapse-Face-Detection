# Multi-Camera Re-ID System

AI-powered multi-camera person detection, tracking, Re-ID, face fusion, behavior analytics, and operator UIs.

## Interfaces

| UI | Persistence | Role |
|----|-------------|------|
| **Streamlit** (`dashboard/app.py`) | SQLite `IdentityStore` | Legacy/fallback operator UI — **keep working** |
| **React** (`frontend/`) | FastAPI → PostgreSQL / Qdrant / Redis | New primary operator UI |

Canonical identity key: **`global_id`** (e.g. `PERSON_0007`). Local tracks stay camera-scoped (e.g. `CAM01-T17`).

## Quick start

```bash
# 1. Infra (requires Docker Desktop running)
docker compose -f docker/docker-compose.yml up -d postgres qdrant redis

# 2. Env
cp .env.example .env

# 3. API
pip install -r requirements-dev.txt
uvicorn api.main:app --reload --port 8000

# 4. React
cd frontend && cp .env.example .env && npm install && npm run dev

# 5. Legacy Streamlit
streamlit run dashboard/app.py
```

## Sample pipeline

```bash
python pipeline.py --videos videos/cam01.mp4 videos/cam02.mp4
```

## Model weights

```bash
python scripts/download_models.py --check
```

If weights are missing you will get a clear instruction — not an obscure stack trace when using the helper.

## Tests

```bash
pytest tests/test_api_unit.py -q
cd frontend && npm run build
```

## Status

See `docs/ARCHITECTURE_AUDIT.md` and `docs/IMPLEMENTATION_STATUS.md` for evidence-based status.  
Do not assume “100% complete” unless `docs/FINAL_VERIFICATION_REPORT.md` shows all acceptance tests PASS.
