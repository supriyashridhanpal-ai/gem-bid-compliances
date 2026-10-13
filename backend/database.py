
import sqlite3
from pathlib import Path

# Store the database inside the backend folder
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "reviews.db"


def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


def initialize_database():
    with get_connection() as connection:
        connection.execute("""
            CREATE TABLE IF NOT EXISTS reviews (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                filename TEXT NOT NULL,
                requirements TEXT NOT NULL,
                result_summary TEXT NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)


def save_review(filename, requirements, result_summary):
    with get_connection() as connection:
        connection.execute("""
            INSERT INTO reviews
                (filename, requirements, result_summary)
            VALUES (?, ?, ?)
        """, (filename, requirements, result_summary))


def get_all_reviews():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT id, filename, requirements,
                   result_summary, created_at
            FROM reviews
            ORDER BY id DESC
        """).fetchall()

        return [dict(row) for row in rows]


if __name__ == "__main__":
    initialize_database()
    print("Database initialized successfully!")
