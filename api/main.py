# api/main.py
from __future__ import annotations

from datetime import datetime
from contextlib import asynccontextmanager
import logging
import sys
import os

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm
import uvicorn

from api.routes import persons, cameras, tracks, search, analytics, websocket, admin
from api.routes import metrics_route
from api.middleware import logging as logging_middleware
from api.middleware import metrics_mw
from api.middleware import security as security_middleware
from api.middleware.cors import get_allowed_origins
from api.dependencies.database import init_db, close_db, dependency_status, is_ready
from api.dependencies.auth import login_for_access_token, Token
from api.schemas.response import ResponseModel, ErrorResponse, ReadyResponse

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler("api.log"),
    ],
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    logger.info("Starting FastAPI application...")
    await init_db()
    logger.info("Startup complete (check /ready for dependency status)")
    yield
    logger.info("Shutting down FastAPI application...")
    await close_db()
    logger.info("Database connections closed")


app = FastAPI(
    title="Multi-Camera Re-ID System API",
    description=(
        "API for multi-camera person tracking and identification.\n\n"
        "Canonical identity key: **global_id** (e.g. PERSON_0007).\n"
        "Local tracks use camera-scoped track IDs (e.g. CAM01-T17)."
    ),
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=get_allowed_origins(),
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

allowed_hosts = os.environ.get("ALLOWED_HOSTS", "*")
app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=[h.strip() for h in allowed_hosts.split(",") if h.strip()],
)

app.middleware("http")(logging_middleware.log_requests)
app.middleware("http")(metrics_mw.record_metrics)
app.middleware("http")(security_middleware.security_and_rate_limit)

# Primary routes under /api (prompt contract)
app.include_router(persons.router, prefix="/api", tags=["persons"])
app.include_router(cameras.router, prefix="/api", tags=["cameras"])
app.include_router(tracks.router, prefix="/api", tags=["tracks"])
app.include_router(search.router, prefix="/api", tags=["search"])
app.include_router(analytics.router, prefix="/api", tags=["analytics"])
app.include_router(websocket.router, prefix="/api", tags=["websocket"])
app.include_router(admin.router, prefix="/api", tags=["admin"])

# Compatibility aliases under /api/v1
app.include_router(persons.router, prefix="/api/v1", tags=["persons-v1"])
app.include_router(cameras.router, prefix="/api/v1", tags=["cameras-v1"])
app.include_router(tracks.router, prefix="/api/v1", tags=["tracks-v1"])
app.include_router(search.router, prefix="/api/v1", tags=["search-v1"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics-v1"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket-v1"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin-v1"])
app.include_router(metrics_route.router, tags=["monitoring"])


@app.post("/api/auth/login", response_model=Token, tags=["auth"])
@app.post("/auth/login", response_model=Token, tags=["auth"])
async def auth_login(form_data: OAuth2PasswordRequestForm = Depends()):
    return await login_for_access_token(form_data)


@app.get("/health", tags=["system"])
async def health_check():
    """Liveness-oriented health (process up). Prefer /live and /ready for probes."""
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "version": "1.0.0",
        "ready": is_ready(),
        "dependencies": dependency_status(),
    }


@app.get("/live", tags=["system"])
async def live():
    """Process is alive."""
    return {
        "status": "alive",
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }


@app.get("/ready", response_model=ReadyResponse, tags=["system"])
async def ready():
    """Ready only when PostgreSQL, Qdrant, and Redis are available."""
    deps = dependency_status()
    ready_flag = is_ready()
    payload = {
        "status": "ready" if ready_flag else "not_ready",
        "dependencies": deps,
        "timestamp": datetime.utcnow(),
    }
    if not ready_flag:
        return JSONResponse(status_code=status.HTTP_503_SERVICE_UNAVAILABLE, content={
            "status": "not_ready",
            "dependencies": deps,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        })
    return payload


@app.get("/", response_class=HTMLResponse)
async def root():
    return """
    <html>
      <head><title>Multi-Camera Re-ID System API</title></head>
      <body style="font-family: system-ui; max-width: 720px; margin: 40px auto;">
        <h1>Multi-Camera Re-ID System</h1>
        <p>Version 1.0.0</p>
        <ul>
          <li><a href="/docs">OpenAPI docs</a></li>
          <li><a href="/health">/health</a></li>
          <li><a href="/live">/live</a></li>
          <li><a href="/ready">/ready</a></li>
        </ul>
      </body>
    </html>
    """


@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=str(exc.detail),
            status_code=exc.status_code,
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).model_dump() if hasattr(ErrorResponse, "model_dump") else ErrorResponse(
            error=str(exc.detail),
            status_code=exc.status_code,
            timestamp=datetime.utcnow().isoformat() + "Z",
        ).dict(),
    )


@app.exception_handler(Exception)
async def general_exception_handler(request, exc: Exception):
    logger.error("Unhandled exception: %s", exc, exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content={
            "error": "Internal server error",
            "status_code": 500,
            "timestamp": datetime.utcnow().isoformat() + "Z",
        },
    )


if __name__ == "__main__":
    host = os.environ.get("API_HOST", "0.0.0.0")
    port = int(os.environ.get("API_PORT", "8000"))
    uvicorn.run("api.main:app", host=host, port=port, reload=True, log_level="info")
