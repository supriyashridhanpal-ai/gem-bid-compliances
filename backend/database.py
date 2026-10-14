import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "reviews.db"


def get_db():
    """Connect to the SQLite database."""
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn


def initialize_database():
    """Create missing tables and update compatible older schemas."""

    with get_db() as conn:
        conn.executescript("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                requirements TEXT NOT NULL,
                summary TEXT,
                result_summary TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            );

            CREATE TABLE IF NOT EXISTS companies (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                name TEXT NOT NULL,
                email TEXT UNIQUE NOT NULL,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS tenders (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                requirements TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS submissions (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                company_id INTEGER,
                tender_id INTEGER,
                filename TEXT,
                extracted_text TEXT,
                status TEXT DEFAULT 'Submitted'
            );

            CREATE TABLE IF NOT EXISTS verification_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                submission_id INTEGER,
                matched TEXT,
                missing TEXT,
                score REAL,
                status TEXT
            );
        """)

        # Read the actual columns in the existing reviews table.
        columns = conn.execute(
            "PRAGMA table_info(reviews)"
        ).fetchall()

        existing_columns = {
            column["name"]: column
            for column in columns
        }

        # Add missing optional columns without deleting existing records.
        for column_name in ("summary", "result_summary"):
            if column_name not in existing_columns:
                conn.execute(
                    f"ALTER TABLE reviews ADD COLUMN {column_name} TEXT"
                )


def save_review(filename, requirements, summary):
    """Save a verification summary using the existing database schema."""

    with get_db() as conn:
        columns = conn.execute(
            "PRAGMA table_info(reviews)"
        ).fetchall()

        # Identify columns that are required and have no default value.
        required_columns = [
            column["name"]
            for column in columns
            if column["notnull"]
            and column["dflt_value"] is None
            and column["pk"] == 0
        ]

        values = {
            "filename": filename,
            "requirements": requirements,
            "summary": summary,
            "result_summary": summary,
        }

        # Refuse to insert if an older database has another required
        # column that this function cannot safely populate.
        supported_columns = {
            "filename",
            "requirements",
            "summary",
            "result_summary",
        }

        unsupported = [
            name for name in required_columns
            if name not in supported_columns
        ]

        if unsupported:
            raise RuntimeError(
                "The reviews table has additional required columns: "
                + ", ".join(unsupported)
                + ". Inspect the table schema before inserting."
            )

        insert_columns = [
            name for name in values
            if name in {column["name"] for column in columns}
        ]

        placeholders = ", ".join("?" for _ in insert_columns)
        column_sql = ", ".join(insert_columns)
        parameters = [values[name] for name in insert_columns]

        cursor = conn.execute(
            f"""
            INSERT INTO reviews ({column_sql})
            VALUES ({placeholders})
            """,
            parameters,
        )

        return cursor.lastrowid


def get_all_reviews():
    """Return verification history, newest first."""

    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reviews ORDER BY id DESC"
        ).fetchall()

        return [dict(row) for row in rows]


def get_review_by_id(review_id):
    """Retrieve one verification record."""

    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reviews WHERE id = ?",
            (review_id,),
        ).fetchone()

        return dict(row) if row else None


def register_company(name, email, username, password_hash):
    """Register a company using a password hash."""

    with get_db() as conn:
        cursor = conn.execute(
            """
            INSERT INTO companies (name, email, username, password)
            VALUES (?, ?, ?, ?)
            """,
            (name, email, username, password_hash),
        )

        return cursor.lastrowid


def login_company(username):
    """Find a company using its username or email."""

    with get_db() as conn:
        row = conn.execute(
            """
            SELECT * FROM companies
            WHERE username = ? OR email = ?
            """,
            (username, username),
        ).fetchone()

        return dict(row) if row else None