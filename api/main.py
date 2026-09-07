# api/main.py
from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
import uvicorn
from contextlib import asynccontextmanager
import logging
import sys
import os

from .routes import persons, cameras, tracks, search, analytics, websocket, admin
from .middleware import auth, cors, logging as logging_middleware
from .dependencies.database import init_db, close_db
from .schemas.response import ResponseModel, ErrorResponse

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler('api.log')
    ]
)
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan manager for startup/shutdown events."""
    # Startup
    logger.info("🚀 Starting FastAPI application...")
    await init_db()
    logger.info("✅ Database initialized")
    yield
    # Shutdown
    logger.info("🛑 Shutting down FastAPI application...")
    await close_db()
    logger.info("✅ Database connections closed")

# Create FastAPI app
app = FastAPI(
    title="Multi-Camera Re-ID System API",
    description="""
    ## Multi-Camera Person Re-Identification System
    
    This API provides endpoints for:
    - Person tracking and identification
    - Camera management
    - Intelligent search
    - Analytics and reporting
    - Real-time WebSocket updates
    
    ### Authentication
    Use the `/auth/login` endpoint to get a JWT token.
    """,
    version="1.0.0",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_tags=[
        {
            "name": "persons",
            "description": "Operations with persons"
        },
        {
            "name": "cameras",
            "description": "Operations with cameras"
        },
        {
            "name": "tracks",
            "description": "Operations with tracks"
        },
        {
            "name": "search",
            "description": "Intelligent search operations"
        },
        {
            "name": "analytics",
            "description": "Analytics and statistics"
        },
        {
            "name": "websocket",
            "description": "WebSocket connections"
        },
        {
            "name": "admin",
            "description": "Administrative operations"
        }
    ]
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure appropriately for production
)

# Add custom middleware
app.middleware("http")(logging_middleware.log_requests)

# Include routers
app.include_router(persons.router, prefix="/api/v1", tags=["persons"])
app.include_router(cameras.router, prefix="/api/v1", tags=["cameras"])
app.include_router(tracks.router, prefix="/api/v1", tags=["tracks"])
app.include_router(search.router, prefix="/api/v1", tags=["search"])
app.include_router(analytics.router, prefix="/api/v1", tags=["analytics"])
app.include_router(websocket.router, prefix="/api/v1", tags=["websocket"])
app.include_router(admin.router, prefix="/api/v1", tags=["admin"])

# Health check endpoint
@app.get("/health", tags=["system"])
async def health_check():
    """Health check endpoint."""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "version": "1.0.0"
    }

# Root endpoint
@app.get("/", response_class=HTMLResponse)
async def root():
    """Root endpoint with API information."""
    return """
    <html>
        <head>
            <title>Multi-Camera Re-ID System API</title>
            <style>
                body {
                    font-family: Arial, sans-serif;
                    max-width: 800px;
                    margin: 50px auto;
                    padding: 20px;
                    background: #f5f5f5;
                }
                .container {
                    background: white;
                    padding: 30px;
                    border-radius: 10px;
                    box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                }
                h1 { color: #333; }
                .links { margin-top: 20px; }
                .links a {
                    display: inline-block;
                    margin: 10px;
                    padding: 10px 20px;
                    background: #007bff;
                    color: white;
                    text-decoration: none;
                    border-radius: 5px;
                }
                .links a:hover { background: #0056b3; }
            </style>
        </head>
        <body>
            <div class="container">
                <h1>🎯 Multi-Camera Re-ID System</h1>
                <p>Version 1.0.0</p>
                <p>Production-ready API for multi-camera person tracking and identification.</p>
                <div class="links">
                    <a href="/docs">📚 API Documentation</a>
                    <a href="/redoc">📖 ReDoc Documentation</a>
                    <a href="/health">💚 Health Check</a>
                </div>
            </div>
        </body>
    </html>
    """

# Error handlers
@app.exception_handler(HTTPException)
async def http_exception_handler(request, exc):
    """HTTP exception handler."""
    return JSONResponse(
        status_code=exc.status_code,
        content=ErrorResponse(
            error=exc.detail,
            status_code=exc.status_code,
            timestamp=datetime.now().isoformat()
        ).dict()
    )

@app.exception_handler(Exception)
async def general_exception_handler(request, exc):
    """General exception handler."""
    logger.error(f"Unhandled exception: {exc}", exc_info=True)
    return JSONResponse(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        content=ErrorResponse(
            error="Internal server error",
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            timestamp=datetime.now().isoformat()
        ).dict()
    )

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )