"""
FastAPI application for the SIMA API.
"""

import logging
from contextlib import asynccontextmanager

import uvicorn
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from sima_storage.database import init_db, close_db

from .settings import settings
from .auth import LoginRequest, TokenResponse, login
from .routes import traces_router, events_router, metrics_router, admin_router
from .websocket import router as websocket_router

# Configure logging
logging.basicConfig(
    level=logging.DEBUG if settings.debug else logging.INFO,
    format="%(asctime)s %(levelname)s %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan handler."""
    logger.info("Starting SIMA API")
    try:
        await init_db()
        logger.info("Database connection established")
    except Exception as e:
        logger.warning(f"Database connection failed: {e}")
    yield
    await close_db()
    logger.info("Shutting down SIMA API")


app = FastAPI(
    title="SIMA API",
    description="Backend API for SIMA web frontend",
    version="0.1.0",
    lifespan=lifespan,
)

# CORS middleware
origins = settings.cors_origins.split(",") if settings.cors_origins != "*" else ["*"]
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(traces_router)
app.include_router(events_router)
app.include_router(metrics_router)
app.include_router(admin_router)
app.include_router(websocket_router)


@app.get("/health")
async def health() -> dict[str, str]:
    """Health check endpoint."""
    return {"status": "healthy"}


@app.get("/")
async def root() -> dict[str, str]:
    """Root endpoint."""
    return {"service": "sima-api", "version": "0.1.0"}


@app.post("/auth/login", response_model=TokenResponse)
async def auth_login(request: LoginRequest) -> TokenResponse:
    """Authenticate and get access token."""
    return login(request.password)


@app.get("/auth/check")
async def auth_check() -> dict[str, bool]:
    """Check if authentication is required."""
    return {"auth_required": bool(settings.lab_password)}


def run():
    """Run the application with uvicorn."""
    uvicorn.run(
        "sima_api.main:app",
        host=settings.host,
        port=settings.port,
        reload=settings.debug,
    )


if __name__ == "__main__":
    run()
