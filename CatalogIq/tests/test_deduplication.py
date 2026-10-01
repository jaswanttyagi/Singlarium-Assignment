import asyncio

import pytest

from app.services.cache_service import CacheService


@pytest.mark.asyncio
async def test_in_flight_deduplication():

    cache = CacheService()

    key = cache.get_content_key(
        "Amul Milk 1L",
        "Fresh full cream milk"
    )

    # First request starts processing
    future = cache.create_in_flight(key)

    # Second request checks whether the same product is already being processed.
    duplicate_future = cache.get_in_flight(key)

    assert duplicate_future is future

    result = {
        "clean_title": "Amul Milk 1L",
        "category": "Groceries",
        "brand": "Amul",
        "tags": ["milk", "dairy"]
    }

    cache.set_result(key, result)

    assert await future == result
    assert await duplicate_future == result

    # After completion the in-flight entry is removed
    assert cache.get_in_flight(key) is None