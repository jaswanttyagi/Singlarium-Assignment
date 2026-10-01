import asyncio
import json
import uuid
from datetime import datetime, timezone

from app.database import get_db_connection
from app.services.cache_service import cache_service
from app.services.llm_services import LLMService


class JobService:

    def __init__(self):
        # LLM service handles retry, concurrency and metrics
        self.llm_service = LLMService()

    def create_job(self, products):
        # Generate a unique ID for the job
        job_id = str(uuid.uuid4())

        conn = get_db_connection()

        conn.execute(
            """
            INSERT INTO jobs (
                id,
                status,
                total,
                created_at
            )
            VALUES (?, ?, ?, ?)
            """,
            (
                job_id,
                "queued",
                len(products),
                datetime.now(timezone.utc).isoformat()
            )
        )

        for product in products:

            conn.execute(
                """
                INSERT OR REPLACE INTO products (
                    sku,
                    raw_title,
                    raw_description,
                    status
                )
                VALUES (?, ?, ?, ?)
                """,
                (
                    product["sku"],
                    product["raw_title"],
                    product.get("raw_description"),
                    "queued"
                )
            )

            conn.execute(
                """
                INSERT OR REPLACE INTO job_items (
                    job_id,
                    sku,
                    status
                )
                VALUES (?, ?, ?)
                """,
                (
                    job_id,
                    product["sku"],
                    "queued"
                )
            )

        conn.commit()
        conn.close()

        # Start processing without blocking the API request
        asyncio.create_task(
            self.process_job(job_id, products)
        )

        return job_id

    async def process_job(self, job_id, products):

        conn = get_db_connection()

        conn.execute(
            """
            UPDATE jobs
            SET status = ?,
                started_at = ?
            WHERE id = ?
            """,
            (
                "running",
                datetime.now(timezone.utc).isoformat(),
                job_id
            )
        )

        conn.commit()
        conn.close()

        # Process all products concurrently
        tasks = [
            self.process_product(job_id, product)
            for product in products
        ]

        results = await asyncio.gather(
            *tasks,
            return_exceptions=True
        )

        conn = get_db_connection()

        conn.execute(
            """
            UPDATE jobs
            SET status = ?,
                finished_at = ?
            WHERE id = ?
            """,
            (
                "completed",
                datetime.now(timezone.utc).isoformat(),
                job_id
            )
        )

        conn.commit()
        conn.close()

    async def process_product(self, job_id, product):

        cache_key = cache_service.get_content_key(
            product["raw_title"],
            product.get("raw_description", "")
        )

        conn = get_db_connection()

        cached = conn.execute(
            """
            SELECT clean_title, category, brand, tags
            FROM products
            WHERE content_key = ?
              AND status = 'enriched'
            LIMIT 1
            """,
            (cache_key,)
        ).fetchone()

        conn.close()

        #use existing enriched result
        if cached:

            try:
                cached_tags = (
                    json.loads(cached["tags"])
                    if cached["tags"]
                    else []
                )
            except (json.JSONDecodeError, TypeError):
                cached_tags = []

            result = {
                "clean_title": cached["clean_title"],
                "category": cached["category"],
                "brand": cached["brand"],
                "tags": cached_tags
            }

            #mark product as enriched because cach already contains the required LLM result.
            conn = get_db_connection()

            conn.execute(
                """
                UPDATE products
                SET clean_title = ?,
                    category = ?,
                    brand = ?,
                    tags = ?,
                    status = ?,
                    error = NULL,
                    content_key = ?
                WHERE sku = ?
                """,
                (
                    result["clean_title"],
                    result["category"],
                    result["brand"],
                    json.dumps(result["tags"]),
                    "enriched",
                    cache_key,
                    product["sku"]
                )
            )

            conn.commit()
            conn.close()

            self._mark_job_item_done(
                job_id,
                product["sku"],
                result,
                cache_hit=True
            )

            return {
                **result,
                "cache_hit": True
            }

        # Check if the same product is already being processed
        in_flight = cache_service.get_in_flight(cache_key)

        if in_flight:

            result = await in_flight

            conn = get_db_connection()

            conn.execute(
                """
                UPDATE products
                SET clean_title = ?,
                    category = ?,
                    brand = ?,
                    tags = ?,
                    status = ?,
                    error = NULL,
                    content_key = ?
                WHERE sku = ?
                """,
                (
                    result["clean_title"],
                    result["category"],
                    result.get("brand"),
                    json.dumps(result.get("tags", [])),
                    "enriched",
                    cache_key,
                    product["sku"]
                )
            )

            conn.commit()
            conn.close()

            self._mark_job_item_done(
                job_id,
                product["sku"],
                result,
                cache_hit=True
            )

            return {
                **result,
                "cache_hit": True
            }

        # Mark this content as currently processing
        cache_service.create_in_flight(cache_key)

        try:

            result = await self.llm_service.enrich(
                product["raw_title"],
                product.get("raw_description", "")
            )

            # Save enriched product in SQLite
            conn = get_db_connection()

            conn.execute(
                """
                UPDATE products
                SET clean_title = ?,
                    category = ?,
                    brand = ?,
                    tags = ?,
                    status = ?,
                    error = NULL,
                    content_key = ?
                WHERE sku = ?
                """,
                (
                    result["clean_title"],
                    result["category"],
                    result.get("brand"),
                    json.dumps(result.get("tags", [])),
                    "enriched",
                    cache_key,
                    product["sku"]
                )
            )

            conn.commit()
            conn.close()

            cache_service.set_result(
                cache_key,
                result
            )

            self._mark_job_item_done(
                job_id,
                product["sku"],
                result,
                cache_hit=False
            )

            return {
                **result,
                "cache_hit": False
            }

        except Exception as error:
            conn = get_db_connection()

            conn.execute(
                """
                UPDATE products
                SET status = ?,
                    error = ?
                WHERE sku = ?
                """,
                (
                    "failed",
                    str(error),
                    product["sku"]
                )
            )

            conn.commit()
            conn.close()
            cache_service.set_error(
                cache_key,
                error
            )

            self._mark_job_item_failed(
                job_id,
                product["sku"],
                str(error)
            )

            raise

    def _mark_job_item_done(
        self,
        job_id,
        sku,
        result,
        cache_hit=False
    ):

        conn = get_db_connection()

        # Mark this product as completed
        conn.execute(
            """
            UPDATE job_items
            SET status = ?,
                error = NULL,
                cache_hit = ?
            WHERE job_id = ?
              AND sku = ?
            """,
            (
                "completed",
                1 if cache_hit else 0,
                job_id,
                sku
            )
        )

        # Update live job progress
        conn.execute(
            """
            UPDATE jobs
            SET done = done + 1,
                cache_hits = cache_hits + ?
            WHERE id = ?
            """,
            (
                1 if cache_hit else 0,
                job_id
            )
        )

        conn.commit()
        conn.close()

    def _mark_job_item_failed(
        self,
        job_id,
        sku,
        error
    ):

        conn = get_db_connection()

        # Mark this product as failed
        conn.execute(
            """
            UPDATE job_items
            SET status = ?,
                error = ?
            WHERE job_id = ?
              AND sku = ?
            """,
            (
                "failed",
                error,
                job_id,
                sku
            )
        )

        conn.execute(
            """
            UPDATE jobs
            SET failed = failed + 1
            WHERE id = ?
            """,
            (job_id,)
        )

        conn.commit()
        conn.close()


job_service = JobService()