import asyncio

# only maximum 3 tries possible excluding initial try
async def retry(operation , max_retries=3, base_delay=0.2):
    for attempt in range(max_retries + 1):
        try:
            return await operation()
        except Exception:
            if attempt == max_retries:
                raise 
            #exception will be raised if max_retries is reached backoff : 200ms -> 400ms...
            delay = base_delay * (2 ** attempt)
            await asyncio.sleep(delay)

