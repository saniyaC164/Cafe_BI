from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from database import SessionLocal
from routers import kpi, mba, inventory, sentiment, forecasting
from middleware import (
    RequestLoggingMiddleware,
    RateLimitMiddleware,
    CacheMiddleware,
    ErrorHandlerMiddleware,
)
import threading 

@asynccontextmanager
async def lifespan(app: FastAPI):
    def warm():
        db = SessionLocal()
        try:
            from services.sentiment_service import _warm_cache
            _warm_cache(db)
        except Exception as e:
            print(f"Cache warming error: {e}")
        finally:
            db.close()

    thread = threading.Thread(target=warm, daemon=True)
    thread.start()
    yield

    
app = FastAPI(
    title="Cafe BI API",
    lifespan=lifespan,
)

# ── Middleware (order matters — outermost runs first on request) ───────────
#
#   Request  →  ErrorHandler  →  Logging  →  RateLimit  →  Cache  →  Route
#   Response ←  ErrorHandler  ←  Logging  ←  RateLimit  ←  Cache  ←  Route
#
app.add_middleware(ErrorHandlerMiddleware)    # 1. catch any uncaught exception
app.add_middleware(RequestLoggingMiddleware)  # 2. log every request + duration
app.add_middleware(RateLimitMiddleware,       # 3. block abusive IPs
    max_requests  = 60,
    window_seconds= 60,
)
app.add_middleware(CacheMiddleware)          # 4. serve cached responses for slow endpoints

# CORS — allow the React frontend to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(kpi.router,         prefix="/api/kpi")
app.include_router(mba.router,         prefix="/api/mba")
app.include_router(inventory.router,   prefix="/api/inventory")
app.include_router(sentiment.router,   prefix="/api/sentiment")
app.include_router(forecasting.router, prefix="/api/forecast")


# ── Health + root ──────────────────────────────────────────────────────────
@app.get("/")
def root():
    return {
        "status":  "running",
        "message": "Cafe BI API is live",
        "docs":    "/docs",
    }


@app.get("/health")
def health():
    return {"status": "ok"}