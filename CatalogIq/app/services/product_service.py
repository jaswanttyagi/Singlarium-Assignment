import json
from app.database import get_db_connection


class ProductService:

    def get_products(self, page=1, limit=20, category=None, search=None):
        # Calculate pagination offset
        offset = (page - 1) * limit

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

        # Filter by category
        if category:
            query += " AND category = ?"
            params.append(category)

        if search:
            query += """
                AND (
                    clean_title LIKE ?
                    OR raw_title LIKE ?
                )
            """

            search_value = f"%{search}%"
            params.extend([search_value, search_value])

        # Newest products first
        query += """
            ORDER BY rowid DESC
            LIMIT ? OFFSET ?
        """

        params.extend([limit, offset])

        rows = conn.execute(query, params).fetchall()

        count_query = """
            SELECT COUNT(*)
            FROM products
            WHERE 1 = 1
        """

        count_params = []

        if category:
            count_query += " AND category = ?"
            count_params.append(category)

        if search:
            count_query += """
                AND (
                    clean_title LIKE ?
                    OR raw_title LIKE ?
                )
            """

            search_value = f"%{search}%"
            count_params.extend([search_value, search_value])

        total = conn.execute(
            count_query,
            count_params
        ).fetchone()[0]

        conn.close()

        products = []

        for row in rows:
            product = dict(row)

            # Convert stored JSON string back into a Python list
            try:
                product["tags"] = json.loads(product["tags"]) \
                    if product["tags"] else []
            except (json.JSONDecodeError, TypeError):
                product["tags"] = []

            products.append(product)

        return {
            "products": products,
            "page": page,
            "limit": limit,
            "total": total
        }

    def get_product(self, sku):
        conn = get_db_connection()

        print("LOOKING FOR SKU:", repr(sku))

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

        print("FOUND ROW:", row)

        conn.close()

        if not row:
            return None

        product = dict(row)

        try:
            product["tags"] = json.loads(product["tags"]) \
                if product["tags"] else []
        except (json.JSONDecodeError, TypeError):
            product["tags"] = []

        return product

    def update_product(self, sku, data):
        # Check whether the product exists
        conn = get_db_connection()

        existing = conn.execute(
            "SELECT sku FROM products WHERE sku = ?",
            (sku,)
        ).fetchone()

        if not existing:
            conn.close()
            return None

        # Allowed fields that can be manually edited
        allowed_fields = [
            "clean_title",
            "category",
            "brand",
            "tags",
            "status"
        ]

        updates = []
        values = []

        for field in allowed_fields:
            if field in data:
                updates.append(f"{field} = ?")

                if field == "tags":
                    values.append(json.dumps(data[field]))
                else:
                    values.append(data[field])

        # Nothing to update
        if not updates:
            conn.close()
            return self.get_product(sku)

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