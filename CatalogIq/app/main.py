from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from app.database import create_tables
from app.routes.jobs import router as jobs_router
from app.routes.metrics_route import router as metrics_router
from app.routes.products import router as products_router


app = FastAPI()


# sttartup

@app.on_event("startup")
def startup_event():
    create_tables()


# ============================================
# API Routes
# ============================================

app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(products_router)


# ============================================
# Health Check
# ============================================

@app.get("/api/health")
def health_check():
    return {"status": "ok"}


BASE_DIR = Path(__file__).resolve().parent.parent

FRONTEND_DIR = BASE_DIR / "frontend"

app.mount(
    "/frontend",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)