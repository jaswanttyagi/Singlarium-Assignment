from fastapi import APIRouter, Query, HTTPException

from app.services.product_service import product_service


router = APIRouter()


# Get Products

@router.get("/api/products")
def get_products(
    page: int = Query(1, ge=1),
    limit: int = Query(20, ge=1, le=100),
    category: str | None = None,
    search: str | None = None
):
    return product_service.get_products(
        page=page,
        limit=limit,
        category=category,
        search=search
    )


# Get Single Product

@router.get("/api/products/{sku}")
def get_product(sku: str):

    product = product_service.get_product(sku)

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product


# Update Product

@router.patch("/api/products/{sku}")
def update_product(
    sku: str,
    data: dict
):

    product = product_service.update_product(
        sku,
        data
    )

    if not product:
        raise HTTPException(
            status_code=404,
            detail="Product not found"
        )

    return product