import asyncio
import json
from google import genai

from app.config import GEMINI_API_KEY, GEMINI_MODEL
from app.providers.base import BaseLLMProvider


class GeminiProvider(BaseLLMProvider):

    def __init__(self):
        if not GEMINI_API_KEY:
            raise ValueError("GEMINI_API_KEY is not configured")

        self.client = genai.Client(
            api_key=GEMINI_API_KEY
        )

    async def enrich(self, raw_title, raw_description=""):

        prompt = f"""
You are a product catalogue enrichment system.

Given the following product:

Title: {raw_title}
Description: {raw_description}

Return ONLY valid JSON with exactly these fields:

{{
  "clean_title": "string",
  "category": "one allowed category",
  "brand": "string or null",
  "tags": ["lowercase", "tags"]
}}

Allowed categories:
Groceries
Beverages
Personal Care
Household
Electronics
Fashion
Home & Kitchen
Other

Rules:
- category must be exactly one of the allowed categories
- brand must be a string or null
- tags must contain at most 5 lowercase strings
- do not add markdown
- return JSON only
"""

        # Gemini SDK call is synchronous, so run it outside the event loop
        response = await asyncio.to_thread(
            self.client.models.generate_content,
            model=GEMINI_MODEL,
            contents=prompt,
            config={
                "response_mime_type": "application/json"
            }
        )

        return json.loads(response.text)