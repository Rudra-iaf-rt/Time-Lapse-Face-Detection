# API

Base URL from `API_HOST` / `API_PORT` (default `http://localhost:8000`).

## System

| Method | Path | Auth | Notes |
|--------|------|------|-------|
| GET | `/health` | no | Process health + dependency snapshot |
| GET | `/live` | no | Liveness |
| GET | `/ready` | no | 200 only if Postgres+Qdrant+Redis OK; else 503 |
| GET | `/docs` | no | OpenAPI |

## Auth

| Method | Path | Notes |
|--------|------|-------|
| POST | `/api/auth/login` | OAuth2 password form → JWT |

Roles: `ADMIN`, `OPERATOR`, `VIEWER`.

## Resources (JWT required unless noted)

- `GET/POST /api/persons`
- `GET /api/persons/{global_id}`
- `POST /api/persons/{global_id}/notes|resolve|reactivate`
- `GET /api/persons/{global_id}/timeline`
- `GET/POST /api/search`, `GET /api/search/persons|events|transitions`
- `GET/POST /api/cameras`, `GET /api/cameras/topology/graph`
- `GET /api/tracks`
- `GET /api/analytics/*`
- `GET /api/admin/*`
- `WS /api/ws/{client_id}`

Compatibility aliases also mounted under `/api/v1/*`.
