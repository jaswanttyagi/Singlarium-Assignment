import csv
import io

from fastapi import APIRouter, HTTPException , UploadFile , File
from app.services.job_service import job_service
from app.database import get_db_connection


router = APIRouter()


@router.post("/api/jobs", status_code=202)
async def create_job(data: dict):

    products = data.get("products")

    # Validate that products list exists and is not empty
    if not products:
        raise HTTPException(
            status_code=400,
            detail="Products list cannot be empty"
        )

    for product in products:
        if not product.get("sku"):
            raise HTTPException(
                status_code=400,
                detail="SKU is required"
            )

        if not product.get("raw_title"):
            raise HTTPException(
                status_code=400,
                detail="raw_title is required"
            )

    # Create and start the background job
    job_id = job_service.create_job(products)

    return {
        "id": job_id,
        "status": "queued",
        "total": len(products),
        "done": 0,
        "failed": 0,
        "cache_hits": 0
    }


# /api/jobs/id  -: with the help of these we check the job status and their progress

@router.get("/api/jobs/{job_id}")
async def get_job(job_id: str):
    conn = get_db_connection()
    job = conn.execute(
        """
        SELECT
          id,
          status,
          total,
          done,
          failed,
          cache_hits,
          created_at,
          started_at,
          finished_at
        FROM jobs
        WHERE id = ?
        """,
        (job_id,)
    ).fetchone()
    conn.close()

    # if job is not present
    if  not job:
        raise HTTPException(
            status_code=404,
            detail="job not found"
        )
    return dict(job)



@router.post("/api/jobs/csv", status_code=202)
async def create_csv_job(file: UploadFile = File(...)):
    # Check that the uploaded file is a CSV
    if not file.filename or not file.filename.lower().endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are allowed"
        )

    # Read uploaded CSV file
    content = await file.read()

    try:
        text = content.decode("utf-8-sig")
    except UnicodeDecodeError:
        raise HTTPException(
            status_code=400,
            detail="CSV must be UTF-8 encoded"
        )

    reader = csv.DictReader(io.StringIO(text))

    required_columns = {
        "sku",
        "raw_title",
        "raw_description"
    }

    if not reader.fieldnames or not required_columns.issubset(
        set(reader.fieldnames)
    ):
        raise HTTPException(
            status_code=400,
            detail="CSV must contain sku, raw_title and raw_description columns"
        )

    products = []

    for row_number, row in enumerate(reader, start=2):
        sku = (row.get("sku") or "").strip()
        raw_title = (row.get("raw_title") or "").strip()
        raw_description = (row.get("raw_description") or "").strip()

        # Validating each row
        if not sku:
            raise HTTPException(
                status_code=400,
                detail=f"SKU is missing at row {row_number}"
            )

        if not raw_title:
            raise HTTPException(
                status_code=400,
                detail=f"raw_title is missing at row {row_number}"
            )

        products.append({
            "sku": sku,
            "raw_title": raw_title,
            "raw_description": raw_description
        })

    if not products:
        raise HTTPException(
            status_code=400,
            detail="CSV contains no products"
        )

    job_id = job_service.create_job(products)

    return {
        "id": job_id,
        "status": "queued",
        "total": len(products),
        "done": 0,
        "failed": 0,
        "cache_hits": 0
    }