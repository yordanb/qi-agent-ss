"""QI Agent SS — FastAPI application entry point."""
import logging
import sys
import time

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

from app.core.config import settings
from app.api.v1.router import api_router

# Structured logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(name)s | %(message)s",
    stream=sys.stdout,
    force=True,
)
logger = logging.getLogger("qi-agent")

app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    docs_url="/docs",
    redoc_url="/redoc",
)

# CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Request logging + error handling middleware
@app.middleware("http")
async def log_requests(request: Request, call_next):
    start = time.time()
    try:
        response = await call_next(request)
        duration = time.time() - start
        logger.info(
            "%s %s → %s (%.0fms)",
            request.method,
            request.url.path,
            response.status_code,
            duration * 1000,
        )
        return response
    except Exception as e:
        duration = time.time() - start
        logger.error(
            "%s %s → ERROR: %s (%.0fms)",
            request.method,
            request.url.path,
            str(e),
            duration * 1000,
        )
        return JSONResponse(status_code=500, content={"detail": "Internal server error"})


# Health check
@app.get("/health")
async def health_check():
    return {"status": "ok", "version": settings.APP_VERSION}


# API v1 routes
app.include_router(api_router, prefix="/api/v1")
