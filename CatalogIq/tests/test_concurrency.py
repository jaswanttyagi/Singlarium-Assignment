import asyncio

import pytest

from app.services.concurrency import ConcurrencyLimiter


@pytest.mark.asyncio
async def test_concurrency_limit():

    limiter = ConcurrencyLimiter()

    active_calls = 0
    max_active_calls = 0

    async def operation():

        nonlocal active_calls
        nonlocal max_active_calls

        active_calls += 1

        max_active_calls = max(
            max_active_calls,
            active_calls
        )

        await asyncio.sleep(0.05)

        active_calls -= 1

        return "done"

    tasks = [
        limiter.run(operation)
        for _ in range(10)
    ]

    results = await asyncio.gather(*tasks)

    assert results == ["done"] * 10

    assert max_active_calls <= 5