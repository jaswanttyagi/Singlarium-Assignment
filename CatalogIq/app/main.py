from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from app.config import LLM_PROVIDER, LLM_CONCURRENCY
from app.database import create_tables
from app.routes.jobs import router as jobs_router
from app.routes.metrics_route import router as metrics_router
from app.routes.products import router as products_router
from fastapi import Request, HTTPException
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse


app = FastAPI()

@app.exception_handler(HTTPException)
async def http_exception_handler(
    request: Request,
    exc: HTTPException
):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "error": str(exc.detail)
        }
    )


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(
    request: Request,
    exc: RequestValidationError
):
    return JSONResponse(
        status_code=400,
        content={
            "error": "Invalid request"
        }
    )


@app.exception_handler(Exception)
async def general_exception_handler(
    request: Request,
    exc: Exception
):
    return JSONResponse(
        status_code=500,
        content={
            "error": str(exc)
        }
    )

# Startup

@app.on_event("startup")
def startup_event():
    create_tables()
# API Routes

app.include_router(jobs_router)
app.include_router(metrics_router)
app.include_router(products_router)


# Health Check
@app.get("/api/health")
def health_check():
    return {
        "status": "ok",
        "llm_provider": LLM_PROVIDER,
        "llm_concurrency": LLM_CONCURRENCY
    }


# ============================================
# Frontend
# ============================================

BASE_DIR = Path(__file__).resolve().parent.parent
FRONTEND_DIR = BASE_DIR / "frontend"


# Keep /frontend available for frontend assets
app.mount(
    "/frontend",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend"
)


# Serve the main frontend at /
app.mount(
    "/",
    StaticFiles(directory=FRONTEND_DIR, html=True),
    name="frontend_root"
)