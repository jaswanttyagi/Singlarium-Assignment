import asyncio
import random

from app.config import MOCK_LATENCY_MS, MOCK_FAILURE_RATE


CATEGORIES = [
    "Groceries",
    "Beverages",
    "Personal Care",
    "Household",
    "Electronics",
    "Fashion",
    "Home & Kitchen",
    "Other",
]


class MockProvider:

    async def enrich(self, raw_title, raw_description=""):
        # Simulate LLM latency
        await asyncio.sleep(MOCK_LATENCY_MS / 1000)

        # Simulate random failure
        if random.random() < MOCK_FAILURE_RATE:
            raise Exception("Mock LLM failed")

        return {
            "clean_title": raw_title.strip(),
            "category": self.detect_category(raw_title),
            "brand": None,
            "tags": []
        }

    def detect_category(self, title):
        title = title.lower()

        if any(word in title for word in ["butter", "milk", "bread", "rice"]):
            return "Groceries"

        if any(word in title for word in ["juice", "coffee", "tea", "drink"]):
            return "Beverages"

        if any(word in title for word in ["shampoo", "soap", "cream"]):
            return "Personal Care"

        if any(word in title for word in ["phone", "laptop", "charger"]):
            return "Electronics"

        return "Other"