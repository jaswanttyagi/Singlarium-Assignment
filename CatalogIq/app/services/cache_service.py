import asyncio
import hashlib
import re


class CacheService:

    def __init__(self):
        # Keeps track of products whose enrichment is currently running
        self.in_flight = {}

    def normalize_content(self, raw_title, raw_description=""):
        # Combine title and description
        content = f"{raw_title} {raw_description}"

        # Lowercase and collapse multiple spaces
        content = re.sub(r"\s+", " ", content.lower()).strip()

        return content

    def get_content_key(self, raw_title, raw_description=""):
        # Generate a stable key for normalized product content
        normalized = self.normalize_content(
            raw_title,
            raw_description
        )

        return hashlib.sha256(
            normalized.encode("utf-8")
        ).hexdigest()

    def create_in_flight(self, key):
        # Create a Future for duplicate requests to wait for
        future = asyncio.get_running_loop().create_future()

        self.in_flight[key] = future

        return future

    def get_in_flight(self, key):
        # Return an existing in-flight operation if present
        return self.in_flight.get(key)

    def set_result(self, key, result):
        # Give the result to requests waiting for the same content
        future = self.in_flight.get(key)

        if future and not future.done():
            future.set_result(result)

        self.in_flight.pop(key, None)

    def set_error(self, key, error):
        # Notify duplicate requests if enrichment fails
        future = self.in_flight.get(key)

        if future and not future.done():
            future.set_exception(error)

        self.in_flight.pop(key, None)


cache_service = CacheService()