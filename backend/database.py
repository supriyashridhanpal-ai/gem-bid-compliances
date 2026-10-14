import sqlite3
from pathlib import Path


# 1. Set the database file location
BASE_DIR = Path(__file__).resolve().parent
DB_PATH = BASE_DIR / "reviews.db"


# 2. Connect to the SQLite database
def get_connection():
    connection = sqlite3.connect(DB_PATH)
    connection.row_factory = sqlite3.Row
    return connection


# 3. Create the database table
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

    print("Database initialized successfully!")


# 4. Save a compliance verification record
def save_review(filename, requirements, result_summary):
    with get_connection() as connection:
        cursor = connection.execute("""
            INSERT INTO reviews (
                filename,
                requirements,
                result_summary
            )
            VALUES (?, ?, ?)
        """, (filename, requirements, result_summary))

        review_id = cursor.lastrowid

    return review_id


# 5. Retrieve all verification records
def get_all_reviews():
    with get_connection() as connection:
        rows = connection.execute("""
            SELECT
                id,
                filename,
                requirements,
                result_summary,
                created_at
            FROM reviews
            ORDER BY id DESC
        """).fetchall()

    # Convert database rows into a list of dictionaries
    return [dict(row) for row in rows]


# 6. Retrieve one record using its ID
def get_review_by_id(review_id):
    with get_connection() as connection:
        row = connection.execute("""
            SELECT
                id,
                filename,
                requirements,
                result_summary,
                created_at
            FROM reviews
            WHERE id = ?
        """, (review_id,)).fetchone()

    if row is None:
        return None

    return dict(row)


# 7. Delete one verification record
def delete_review(review_id):
    with get_connection() as connection:
        cursor = connection.execute("""
            DELETE FROM reviews
            WHERE id = ?
        """, (review_id,))

        deleted = cursor.rowcount > 0

    return deleted


# 8. Run this file directly to initialize and test the database
if __name__ == "__main__":
    initialize_database()

    print("\nExisting verification records:")

    reviews = get_all_reviews()

    if reviews:
        for review in reviews:
            print(review)
    else:
        print("No verification records found.")