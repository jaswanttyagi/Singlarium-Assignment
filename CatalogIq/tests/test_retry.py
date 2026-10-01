import pytest

from app.services.retry_service import retry


@pytest.mark.asyncio
async def test_retry_succeeds_after_failures():

    attempts = 0

    async def operation():

        nonlocal attempts

        attempts += 1

        if attempts < 3:
            raise Exception("Temporary failure")

        return "success"

    result = await retry(
        operation,
        max_retries=3,
        base_delay=0
    )

    assert result == "success"
    assert attempts == 3


@pytest.mark.asyncio
async def test_retry_fails_after_max_retries():

    attempts = 0

    async def operation():

        nonlocal attempts

        attempts += 1

        raise Exception("Permanent failure")

    with pytest.raises(Exception, match="Permanent failure"):

        await retry(
            operation,
            max_retries=3,
            base_delay=0
        )

    #initial attempt + 3 retries = 4 attempts
    assert attempts == 4