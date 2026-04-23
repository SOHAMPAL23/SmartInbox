"""
app/main.py
-----------
FastAPI application entrypoint for the SmartInbox SMS Spam Detection API.

Start:  uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
Docs:   http://localhost:8000/docs   (Swagger UI)
        http://localhost:8000/redoc  (ReDoc)
"""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.middleware.gzip import GZipMiddleware

from app.core.config import get_settings
from app.core.logging import configure_logging, get_logger
from app.database import create_tables
from app.middleware import GlobalExceptionMiddleware, RequestLoggingMiddleware
from app.routers import admin, auth, user, notifications, ws, jobs
from app.services.ml_service import init_spam_detector

settings = get_settings()

# ── Configure logging before anything else ────────────────────────────────────
configure_logging()
logger = get_logger("main")


# ── Rate limiter setup ────────────────────────────────────────────────────────
try:
    from slowapi import Limiter, _rate_limit_exceeded_handler
    from slowapi.util import get_remote_address
    from slowapi.errors import RateLimitExceeded

    limiter = Limiter(key_func=get_remote_address, default_limits=["200/minute"])
    _rate_limit_available = True
except ImportError:
    limiter = None
    _rate_limit_available = False
    logger.warning("slowapi not installed – rate limiting disabled.")


# ── Lifespan (startup / shutdown) ─────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastAPI):
    """
    Application lifespan manager.
    Startup:  create DB tables, load ML model.
    Shutdown: nothing needed (connections managed by SQLAlchemy pool).
    """
    logger.info("═══ SmartInbox API starting up ═══")
    logger.info(
        "Environment: %s | Debug: %s | Model: %s",
        settings.ENVIRONMENT, settings.DEBUG, settings.MODEL_VERSION,
    )

    # ── Database Connectivity Check ───────────────────────────────────────────
    try:
        from app.database import AsyncSessionLocal
        from sqlalchemy import text
        import asyncio
        
        connected = False
        retries = 5
        while not connected and retries > 0:
            try:
                async with AsyncSessionLocal() as session:
                    await session.execute(text("SELECT 1"))
                connected = True
                logger.info("Database connectivity verified. [Neon/Serverless Postgres]")
            except Exception as e:
                retries -= 1
                logger.warning(f"Database connection failed. Retrying in 2s... ({retries} retries left)")
                await asyncio.sleep(2)
        
        if not connected:
            logger.error("Failed to connect to database after multiple retries. API may be degraded.")
        else:
            await create_tables()
            logger.info("Database schema verified / created.")
    except Exception as exc:
        logger.error("Error during database initialization: %s", exc)


    # ── Load ML model into memory ─────────────────────────────────────────────
    try:
        detector = init_spam_detector()
        logger.info(
            "ML model loaded │ version=%s │ threshold=%.4f",
            detector._model_version, detector._threshold,
        )
        # ── Warm-up: prime sklearn pipeline so first real request is fast ─────
        try:
            import time as _time
            _t = _time.perf_counter()
            detector.predict("warm up call to preload numpy internals")
            _ms = (_time.perf_counter() - _t) * 1000
            logger.info("ML warm-up complete │ latency=%.1fms", _ms)
        except Exception as warm_exc:
            logger.warning("ML warm-up skipped: %s", warm_exc)
    except Exception as exc:
        logger.error(
            "ML model failed to load: %s — predictions will be unavailable.", exc
        )

    # ── Background Workers ───────────────────────────────────────────────────
    try:
        import asyncio
        from app.services.precompute_worker import precompute_analytics_loop
        asyncio.create_task(precompute_analytics_loop())
        logger.info("Precompute Analytics Worker started in background.")
    except Exception as e:
        logger.error(f"Failed to start precompute worker: {e}")

    logger.info("═══ SmartInbox API ready ═══")
    yield
    logger.info("═══ SmartInbox API shutting down ═══")


# ── FastAPI application ───────────────────────────────────────────────────────

app = FastAPI(
    title       = settings.APP_NAME,
    version     = settings.APP_VERSION,
    description = """
## SmartInbox – SMS Spam Detection API

Production-grade REST API for detecting spam in SMS messages using a
trained ML pipeline with TF-IDF + feature engineering.

### Features
- 🔐 **JWT Authentication** – register, login, token refresh
- 👤 **Role-based Access** – `user` and `admin` roles
- 📨 **Single & Batch Prediction** – classify one or many messages at once
- 📁 **CSV Batch Upload** – upload a CSV file for bulk classification
- 📊 **History & Trends** – paginated prediction history + daily spam trends
- 📤 **CSV Export** – export your history as a downloadable CSV
- 🛠️ **Admin Portal** – user management, global analytics, model management
- 🔁 **Live Retraining** – upload new data and hot-swap the model
- 🎛️ **Dynamic Threshold** – update decision threshold without restart
- ⚠️ **Uncertainty Detection** – low-confidence predictions flagged as UNCERTAIN

### Authentication
All prediction endpoints require a valid JWT.
Use `/auth/login` to obtain a token, then include it as:
```
Authorization: Bearer <access_token>
```
    """,
    docs_url    = "/docs",
    redoc_url   = "/redoc",
    openapi_url = "/openapi.json",
    lifespan    = lifespan,
)

# ── Rate limiter state ────────────────────────────────────────────────────────
if _rate_limit_available and limiter:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# ── Custom middleware ─────────────────────────────────────────────────────────
app.add_middleware(GZipMiddleware, minimum_size=500)
app.add_middleware(GlobalExceptionMiddleware)
app.add_middleware(RequestLoggingMiddleware)

# ── CORS (Must be outermost layer so it adds headers even to 500 errors) ──────
app.add_middleware(
    CORSMiddleware,
    allow_origins     = settings.ALLOWED_ORIGINS,
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers (Standard /api/v1 prefix) ──────────────────────────────────────────
app.include_router(auth.router,          prefix="/api/v1")
app.include_router(user.router,          prefix="/api/v1")
app.include_router(admin.router,         prefix="/api/v1")
app.include_router(notifications.router, prefix="/api/v1")
app.include_router(ws.router,            prefix="/api/v1")
app.include_router(jobs.router,          prefix="/api/v1")

# ── Routers (Root prefix fallback for deployment flexibility) ──────────────────
app.include_router(auth.router)
app.include_router(user.router)
app.include_router(admin.router)
app.include_router(notifications.router)
app.include_router(ws.router)
app.include_router(jobs.router)


# ── Root & health endpoints ───────────────────────────────────────────────────

@app.get("/", tags=["General"], summary="API root – version info")
async def root():
    """Returns basic API version info."""
    return {
        "name":    settings.APP_NAME,
        "version": settings.APP_VERSION,
        "docs":    "/docs",
    }


@app.get(
    "/health",
    tags=["General"],
    summary="Health check – model + database status",
)
async def health_check(request: Request):
    """
    Lightweight health-check endpoint for load balancers and uptime monitors.

    Returns:
    - **status**: `"healthy"` | `"degraded"`
    - **model**: ML model status
    - **database**: DB connectivity check
    - **rate_limiting**: whether slowapi is active
    """
    from app.services.ml_service import _detector

    # ML health
    ml_health = _detector.health() if _detector else {"status": "not_loaded"}

    # DB health (simple connectivity check)
    from app.database import AsyncSessionLocal
    from sqlalchemy import text as sa_text
    db_status = "ok"
    try:
        async with AsyncSessionLocal() as session:
            await session.execute(sa_text("SELECT 1"))
    except Exception as exc:
        logger.warning("DB health check failed: %s", exc)
        db_status = "error"

    overall = "healthy" if (ml_health.get("status") == "healthy" and db_status == "ok") else "degraded"

    return JSONResponse(
        status_code=status.HTTP_200_OK if overall == "healthy" else status.HTTP_206_PARTIAL_CONTENT,
        content={
            "status":         overall,
            "model":          ml_health,
            "database":       db_status,
            "rate_limiting":  _rate_limit_available,
            "version":        settings.APP_VERSION,
        },
    )

@app.get("/debug/logs")
def get_debug_logs():
    import os
    if os.path.exists("logs/api.log"):
        with open("logs/api.log", "r") as f:
            lines = f.readlines()
            return {"logs": lines[-100:]}
    return {"error": "Log file not found"}


# ── Redirect common frontend paths to Amplify ──────────────────────────────────
# This ensures that visiting smartinbox-nopk.onrender.com/login sends you to the real app.
@app.get("/{path:path}", tags=["General"], include_in_schema=False)
async def redirect_to_frontend(path: str):
    """Redirect non-API requests to the Amplify frontend."""
    frontend_url = "https://main.d2tsa0g3cou3c1.amplifyapp.com"
    # Don't redirect API paths or docs (they should have been caught by routers above)
    if path.startswith(("api/", "docs", "redoc", "openapi.json", "debug/")):
        return JSONResponse(status_code=404, content={"detail": "Not Found"})
    
    return RedirectResponse(url=f"{frontend_url}/{path}")

from fastapi.responses import RedirectResponse
