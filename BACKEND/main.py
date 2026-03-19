from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import kpi, mba

app = FastAPI(
    title       = "Cafe BI API",
    description = "Business intelligence backend for cafe analytics",
    version     = "1.0.0",
)

# CORS — allow the React frontend (any localhost port) to call this API
app.add_middleware(
    CORSMiddleware,
    allow_origins     = ["http://localhost:3000", "http://localhost:5173"],
    allow_credentials = True,
    allow_methods     = ["*"],
    allow_headers     = ["*"],
)

# ── Routers ────────────────────────────────────────────────────────────────
app.include_router(kpi.router, prefix="/api/kpi")
app.include_router(mba.router, prefix="/api/mba")

# More routers will be added here as features are built:
# from routers import sentiment, forecasting, inventory
# app.include_router(sentiment.router,   prefix="/api/sentiment")
# app.include_router(forecasting.router, prefix="/api/forecast")
# app.include_router(inventory.router,   prefix="/api/inventory")


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