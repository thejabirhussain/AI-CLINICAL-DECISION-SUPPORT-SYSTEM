"""FastAPI application main module."""

import logging
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.errors import RateLimitExceeded
from slowapi.util import get_remote_address

from app.api.routes_admin import router as admin_router
from app.api.routes_chat import router as chat_router
from app.api.routes_patient import router as patient_router
from app.core.config import settings
from app.core.logging import setup_logging

# Setup logging
setup_logging()
logger = logging.getLogger(__name__)

# Rate limiter
limiter = Limiter(key_func=get_remote_address)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown."""
    logger.info("Starting Clinical Decision Support API")
    yield
    logger.info("Shutting down API")


# Create FastAPI app
app = FastAPI(
    title="Clinical Decision Support API",
    description="AI-powered Clinical Decision Support System with Medical Knowledge RAG",
    version="1.0.0",
    lifespan=lifespan,
)

# Add rate limiter
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(chat_router, prefix="/v1", tags=["chat"])
app.include_router(patient_router, prefix="/patient", tags=["patient"])
app.include_router(admin_router, prefix="/admin", tags=["admin"])


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy", "version": "1.0.0"}


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "name": "Clinical Decision Support API",
        "version": "1.0.0",
        "docs": "/docs",
        "health": "/health",
    }
