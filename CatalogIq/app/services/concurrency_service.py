# this will ensure the how many maximum call go to LLM -> max -: 5 allowed

import asyncio
from app.config import LLM_CONCURRENCY

class ConcurrencyLimiter:

    def __init__(self):
    # we use semaphore to control the maxium number of LLM calls running at same time.
        self.semaphore = asyncio.Semaphore(LLM_CONCURRENCY)

    async def run(self , operation):
        async with self.semaphore:
            return await operation()