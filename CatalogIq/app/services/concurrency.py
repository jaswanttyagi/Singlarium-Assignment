import asyncio

from app.config import LLM_CONCURRENCY


class ConcurrencyLimiter:

    def __init__(self):
        # Limits the number of LLM calls running at the same time
        self.semaphore = asyncio.Semaphore(LLM_CONCURRENCY)

    async def run(self, operation):
        async with self.semaphore:
            # Run the LLM operation when a slot is available
            return await operation()


concurrency_limiter = ConcurrencyLimiter()