# api/routes/metrics_route.py
"""Prometheus metrics endpoint (real request counters when scraped)."""

from fastapi import APIRouter, Response
from prometheus_client import Counter, Histogram, generate_latest, CONTENT_TYPE_LATEST

router = APIRouter()

REQUEST_COUNT = Counter(
    "multicam_http_requests_total",
    "HTTP requests",
    ["method", "endpoint", "status"],
)
REQUEST_LATENCY = Histogram(
    "multicam_http_request_latency_seconds",
    "HTTP request latency",
    ["endpoint"],
)


@router.get("/metrics")
async def metrics():
    return Response(generate_latest(), media_type=CONTENT_TYPE_LATEST)
