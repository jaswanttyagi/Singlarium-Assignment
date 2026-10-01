from app.config import LLM_PROVIDER
from app.providers.mock_provider import MockProvider
from app.providers.gemini_provider import GeminiProvider
from app.services.metrics import metrics
from app.services.concurrency import concurrency_limiter
from app.services.retry_service import retry
from app.services.validation import validate_llm_result

# this code is providing a interface to the LLM service, which can be used to enrich product data using different LLM providers. Currently, it supports a mock provider for testing purposes. The LLMService class initializes the appropriate provider based on the configuration and provides an asynchronous method to enrich product data.
class LLMService:

    def __init__(self):
        if LLM_PROVIDER == "mock":
            self.provider = MockProvider()
        elif LLM_PROVIDER == "gemini":
            self.provider = GeminiProvider()
        else:
            raise ValueError(f"Unsupported LLM provider: {LLM_PROVIDER}")

    
#asynchornous handling here
    async def enrich(self, raw_title, raw_description=""):

        async def call_provider():
        # Record the start of an LLM call
            metrics.call_started()

            try:
            # Call the configured LLM provider
                result =  await self.provider.enrich(
                raw_title,
                raw_description
            )
                return validate_llm_result(result)

            except Exception:
            # Record failed LLM attempt
                metrics.record_error()
                raise

            finally:
            # Record that the LLM call has finished
                metrics.call_finished()

        async def limited_call():
            return await concurrency_limiter.run(call_provider)
        return await retry(limited_call)

        
            