"""
Conflict Tracker API — FastAPI application entry point.
"""
from __future__ import annotations
import sys

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from loguru import logger
from slowapi import _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware

from api.config import get_settings
from api.middleware.rate_limit import limiter
from api.routers import analytics, events, health

settings = get_settings()

# ── Logging setup ────────────────────────────────────────
logger.remove()
logger.add(
    sys.stdout,
    level=settings.log_level,
    format="<green>{time:HH:mm:ss}</green> | <level>{level: <8}</level> | {message}",
    colorize=False,  # Render.com logs don't support ANSI colours
)

# ── App initialisation ───────────────────────────────────
app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Real-time conflict event tracker API. "
        "Aggregates news from BBC, Reuters, Al Jazeera, GDELT and more. "
        "Every article is enriched with NLP sentiment analysis, "
        "named entity recognition, and geocoordinates."
    ),
    docs_url="/docs",
    redoc_url="/redoc",
    openapi_url="/openapi.json",
)

# ── Rate limiter ─────────────────────────────────────────
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── CORS ─────────────────────────────────────────────────
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.cors_origins,
    allow_credentials=True,
    allow_methods=["GET", "OPTIONS"],
    allow_headers=["*"],
)

# ── Routers ──────────────────────────────────────────────
app.include_router(events.router)
app.include_router(analytics.router)
app.include_router(health.router)


# ── Root endpoint ────────────────────────────────────────
@app.get("/", tags=["Root"], include_in_schema=False)
async def root():
    return {
        "name":    settings.app_name,
        "version": settings.app_version,
        "docs":    "/docs",
        "health":  "/health",
    }


# ── Global exception handler ─────────────────────────────
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    logger.error(f"Unhandled exception on {request.url}: {exc}")
    return JSONResponse(
        status_code=500,
        content={"detail": "An unexpected error occurred. Please try again."},
    )


# ── Startup / shutdown events ────────────────────────────
@app.on_event("startup")
async def on_startup():
    logger.info(f"{settings.app_name} v{settings.app_version} started")
    logger.info(f"Docs available at /docs")


@app.on_event("shutdown")
async def on_shutdown():
    logger.info("API shutting down")