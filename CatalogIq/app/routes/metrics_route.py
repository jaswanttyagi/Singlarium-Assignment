from fastapi import APIRouter

from app.services.metrics import metrics


router = APIRouter()


@router.get("/api/metrics")
def get_metrics():
    # Return current LLM metrics
    return metrics.get_metrics()