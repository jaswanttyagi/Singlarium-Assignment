from fastapi import APIRouter, Query, HTTPException

from app.services.product_service import product_service


router = APIRouter()


@router.get("/api/products")
def get_products(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    category: str | None = None,
    q: str | None = None
):
    return product_service.get_products(
        page=page,
        page_size=page_size,
        category=category,
        q=q
    )


@router.get("/api/products/{sku}")
def get_product(sku: str):
    product = product_service.get_product(sku)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


@router.patch("/api/products/{sku}")
def update_product(sku: str, data: dict):
    try:
        product = product_service.update_product(sku, data)

    except ValueError as error:
        raise HTTPException(
            status_code=400,
            detail=str(error)
        )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product