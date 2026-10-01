import json

from app.database import get_db_connection


ALLOWED_CATEGORIES = {
    "Groceries",
    "Beverages",
    "Personal Care",
    "Household",
    "Electronics",
    "Fashion",
    "Home & Kitchen",
    "Other",
}


class ProductService:

    def get_products(
        self,
        page=1,
        page_size=20,
        category=None,
        q=None
    ):
        offset = (page - 1) * page_size

        conn = get_db_connection()

        query = """
            SELECT
                sku,
                raw_title,
                raw_description,
                clean_title,
                category,
                brand,
                tags,
                status,
                error
            FROM products
            WHERE 1 = 1
        """

        params = []

        # Category filter
        if category:
            query += " AND category = ?"
            params.append(category)

        # Case-insensitive search
        if q:
            query += """
                AND (
                    LOWER(COALESCE(clean_title, '')) LIKE LOWER(?)
                    OR LOWER(raw_title) LIKE LOWER(?)
                )
            """

            search_value = f"%{q}%"
            params.extend([search_value, search_value])

        # Assignment requires products sorted by SKU
        query += """
            ORDER BY sku ASC
            LIMIT ? OFFSET ?
        """

        params.extend([page_size, offset])

        rows = conn.execute(
            query,
            params
        ).fetchall()

        # Count total matching products
        count_query = """
            SELECT COUNT(*)
            FROM products
            WHERE 1 = 1
        """

        count_params = []

        if category:
            count_query += " AND category = ?"
            count_params.append(category)

        if q:
            count_query += """
                AND (
                    LOWER(COALESCE(clean_title, '')) LIKE LOWER(?)
                    OR LOWER(raw_title) LIKE LOWER(?)
                )
            """

            search_value = f"%{q}%"
            count_params.extend([search_value, search_value])

        total = conn.execute(
            count_query,
            count_params
        ).fetchone()[0]

        conn.close()

        products = []

        for row in rows:
            product = dict(row)

            try:
                product["tags"] = (
                    json.loads(product["tags"])
                    if product["tags"]
                    else []
                )
            except (json.JSONDecodeError, TypeError):
                product["tags"] = []

            products.append(product)

        return {
            "items": products,
            "page": page,
            "page_size": page_size,
            "total": total
        }

    def get_product(self, sku):
        conn = get_db_connection()

        row = conn.execute(
            """
            SELECT
                sku,
                raw_title,
                raw_description,
                clean_title,
                category,
                brand,
                tags,
                status,
                error
            FROM products
            WHERE sku = ?
            """,
            (sku,)
        ).fetchone()

        conn.close()

        if not row:
            return None

        product = dict(row)

        try:
            product["tags"] = (
                json.loads(product["tags"])
                if product["tags"]
                else []
            )
        except (json.JSONDecodeError, TypeError):
            product["tags"] = []

        return product

    def update_product(self, sku, data):

        conn = get_db_connection()

        existing = conn.execute(
            "SELECT sku FROM products WHERE sku = ?",
            (sku,)
        ).fetchone()

        if not existing:
            conn.close()
            return None

        # Only these fields can be edited from the API
        allowed_fields = {
            "clean_title",
            "category",
            "tags"
        }

        updates = []
        values = []

        # Validate fields
        for field in data:

            if field not in allowed_fields:
                continue

            value = data[field]

            if field == "clean_title":

                if not isinstance(value, str) or not value.strip():
                    conn.close()
                    raise ValueError(
                        "clean_title cannot be empty"
                    )

                value = value.strip()

            elif field == "category":

                if value not in ALLOWED_CATEGORIES:
                    conn.close()
                    raise ValueError(
                        f"Invalid category: {value}"
                    )

            elif field == "tags":

                if not isinstance(value, list):
                    conn.close()
                    raise ValueError(
                        "tags must be a list"
                    )

                if len(value) > 5:
                    conn.close()
                    raise ValueError(
                        "Maximum 5 tags are allowed"
                    )

                for tag in value:
                    if not isinstance(tag, str):
                        conn.close()
                        raise ValueError(
                            "Every tag must be a string"
                        )

                    if tag != tag.lower():
                        conn.close()
                        raise ValueError(
                            "Tags must be lowercase"
                        )

                value = json.dumps(value)

            updates.append(f"{field} = ?")
            values.append(value)

        if not updates:
            conn.close()
            return self.get_product(sku)

        # Manual review/edit means product is approved
        updates.append("status = ?")
        values.append("approved")

        values.append(sku)

        query = f"""
            UPDATE products
            SET {", ".join(updates)}
            WHERE sku = ?
        """

        conn.execute(query, values)
        conn.commit()
        conn.close()

        return self.get_product(sku)


product_service = ProductService()