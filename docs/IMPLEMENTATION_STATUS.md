# Implementation Status

Evidence-based status as of 2026-09-08 (post pipeline E2E). Values: IMPLEMENTED / PARTIALLY IMPLEMENTED / BLOCKED / NOT IMPLEMENTED.

| Area | Status | Evidence |
|------|--------|----------|
| Repository audit | IMPLEMENTED | `docs/ARCHITECTURE_AUDIT.md` |
| FastAPI + health probes | IMPLEMENTED | `/ready` → 200 with pg/qdrant/redis ok |
| JWT auth + RBAC | IMPLEMENTED | form login + Bearer protected routes |
| WebSocket | PARTIALLY IMPLEMENTED | `WS_E2E_PASS` connect/subscribe; broadcast fan-out not fully proven |
| Postgres/Qdrant/Redis | IMPLEMENTED | Docker healthy; API connected (PG on **5433**) |
| Streamlit + SQLite | IMPLEMENTED | preserved; pipeline writes `database/identities.db` |
| Pipeline → API bridge | IMPLEMENTED | IdentityStore list + `sync_sqlite_to_postgres.py` (11 persons) |
| React frontend | IMPLEMENTED | pages + `npm run build` + Vitest 7/7 |
| Sample multi-cam pipeline | IMPLEMENTED | MobileNet CPU run on `cam01`/`cam02`; cross-cam reappear observed |
| Evaluation | IMPLEMENTED | `eval/` + tests |
| Edge | IMPLEMENTED | capability + metadata buffer |
| Docker compose | IMPLEMENTED | postgres/qdrant/redis up |
| Postman/Newman | IMPLEMENTED | 13 requests, 0 failures |
| CI workflows | IMPLEMENTED | `.github/workflows/*` |
| Model weights (OSNet/ArcFace) | BLOCKED | missing `.pth` files |
| Full accuracy ML path | BLOCKED | needs weights |

## Not claiming

- 100% complete
- Fabricated accuracy metrics
- Full OSNet/ArcFace production parity without weights
