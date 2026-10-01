import sqlite3


DATABASE_NAME = "catalogiq.db"


def get_db_connection():
    # Create a connection to the SQLite database
    conn = sqlite3.connect(DATABASE_NAME)

    # Return rows as dictionary-like objects
    conn.row_factory = sqlite3.Row

    return conn


def create_tables():
    conn = get_db_connection()

    conn.execute("""
    CREATE TABLE IF NOT EXISTS jobs(
        id TEXT PRIMARY KEY,
        status TEXT NOT NULL,
        total INTEGER NOT NULL,
        done INTEGER DEFAULT 0,
        failed INTEGER DEFAULT 0,
        cache_hits INTEGER DEFAULT 0,
        created_at TEXT NOT NULL,
        started_at TEXT,
        finished_at TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS products(
        sku TEXT PRIMARY KEY,
        raw_title TEXT NOT NULL,
        raw_description TEXT,
        clean_title TEXT,
        category TEXT,
        brand TEXT,
        tags TEXT,
        status TEXT NOT NULL,
        error TEXT,
        content_key TEXT
    )
    """)

    conn.execute("""
    CREATE TABLE IF NOT EXISTS job_items(
        job_id TEXT NOT NULL,
        sku TEXT NOT NULL,
        status TEXT NOT NULL,
        error TEXT,
        cache_hit INTEGER DEFAULT 0,
        PRIMARY KEY (job_id, sku),
        FOREIGN KEY (job_id) REFERENCES jobs(id),
        FOREIGN KEY (sku) REFERENCES products(sku)
    )
    """)

    # Speed up cache lookups
    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_products_content_key
    ON products(content_key)
    """)

    # Speed up job item lookups
    conn.execute("""
    CREATE INDEX IF NOT EXISTS idx_job_items_job_id
    ON job_items(job_id)
    """)

    conn.commit()
    conn.close()