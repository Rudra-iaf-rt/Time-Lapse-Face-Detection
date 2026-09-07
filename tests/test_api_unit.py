# tests/test_api_unit.py
"""Unit tests for FastAPI app that do not require a pre-started server."""

import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from fastapi.testclient import TestClient


def test_live_endpoint():
    from api.main import app

    with TestClient(app) as client:
        r = client.get("/live")
        assert r.status_code == 200
        assert r.json()["status"] == "alive"


def test_health_endpoint():
    from api.main import app

    with TestClient(app) as client:
        r = client.get("/health")
        assert r.status_code == 200
        body = r.json()
        assert "status" in body
        assert "dependencies" in body


def test_ready_structure():
    from api.main import app

    with TestClient(app) as client:
        r = client.get("/ready")
        # 200 if infra up, 503 if not — both valid structured responses
        assert r.status_code in (200, 503)
        body = r.json()
        assert "status" in body
        assert "dependencies" in body
        for key in ("postgresql", "qdrant", "redis"):
            assert key in body["dependencies"]


def test_docs_available():
    from api.main import app

    with TestClient(app) as client:
        r = client.get("/docs")
        assert r.status_code == 200


def test_login_and_persons_auth():
    from api.main import app

    with TestClient(app) as client:
        # unauthenticated should 401
        r = client.get("/api/persons")
        assert r.status_code == 401

        login = client.post(
            "/api/auth/login",
            data={"username": "admin", "password": "admin-change-me"},
        )
        assert login.status_code == 200
        token = login.json()["access_token"]
        assert token

        r = client.get(
            "/api/persons",
            headers={"Authorization": f"Bearer {token}"},
        )
        # May be 200 with empty/data, or 500 only if store broken — expect 200
        assert r.status_code == 200
        assert r.json()["success"] is True
