
import sqlite3
import json
import sqlite3
from pathlib import Path

DB_NAME = Path(__file__).resolve().parent / "reviews.db"


def get_db():
    conn = sqlite3.connect(DB_NAME, timeout=10)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


def initialize_database():
    """Create missing tables without deleting existing records."""
    with get_db() as conn:
        conn.executescript("""
        CREATE TABLE IF NOT EXISTS companies (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        );

        CREATE TABLE IF NOT EXISTS tenders (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT NOT NULL,
            requirements TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS submissions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER NOT NULL,
            tender_id INTEGER,
            filename TEXT NOT NULL,
            extracted_text TEXT,
            status TEXT DEFAULT 'Uploaded',
            uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(tender_id) REFERENCES tenders(id)
        );

        CREATE TABLE IF NOT EXISTS verification_results (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            submission_id INTEGER UNIQUE NOT NULL,
            requirements_checked TEXT,
            matched TEXT,
            missing TEXT,
            score REAL,
            status TEXT DEFAULT 'Pending',
            result_summary TEXT,
            verified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(submission_id) REFERENCES submissions(id)
        );

        CREATE TABLE IF NOT EXISTS reviews (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            company_id INTEGER,
            submission_id INTEGER,
            filename TEXT NOT NULL,
            requirements TEXT NOT NULL,
            summary TEXT,
            result_summary TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(company_id) REFERENCES companies(id),
            FOREIGN KEY(submission_id) REFERENCES submissions(id)
        );
        """)

        # Add missing columns to compatible older reviews tables.
        columns = {
            row["name"]
            for row in conn.execute("PRAGMA table_info(reviews)")
        }
        for name, kind in {
            "company_id": "INTEGER",
            "submission_id": "INTEGER",
            "summary": "TEXT",
            "result_summary": "TEXT"
        }.items():
            if name not in columns:
                conn.execute(f"ALTER TABLE reviews ADD COLUMN {name} {kind}")
        columns = conn.execute("PRAGMA table_info(reviews)").fetchall()
        existing_columns = {column["name"] for column in columns}
        for column_name in ("summary", "result_summary"):
            if column_name not in existing_columns:
                conn.execute(f"ALTER TABLE reviews ADD COLUMN {column_name} TEXT")


def save_review(filename, requirements, summary):
    """Save a verification summary using the existing database schema."""
    with get_db() as conn:
        columns = conn.execute("PRAGMA table_info(reviews)").fetchall()
        required_columns = [
            col["name"] for col in columns
            if col["notnull"] and col["dflt_value"] is None and col["pk"] == 0
        ]
        values = {
            "filename": filename,
            "requirements": requirements,
            "summary": summary,
            "result_summary": summary,
        }
        supported_columns = set(values)
        unsupported = [name for name in required_columns if name not in supported_columns]
        if unsupported:
            raise RuntimeError(
                "The reviews table has additional required columns: " + ", ".join(unsupported)
            )
        insert_columns = [name for name in values if name in {col["name"] for col in columns}]
        placeholders = ", ".join("?" for _ in insert_columns)
        column_sql = ", ".join(insert_columns)
        parameters = [values[name] for name in insert_columns]
        cursor = conn.execute(
            f"INSERT INTO reviews ({column_sql}) VALUES ({placeholders})", parameters
        )
        return cursor.lastrowid


def get_all_reviews():
    with get_db() as conn:
        rows = conn.execute("SELECT * FROM reviews ORDER BY id DESC").fetchall()
        return [dict(row) for row in rows]


def get_review_by_id(review_id):
    with get_db() as conn:
        row = conn.execute("SELECT * FROM reviews WHERE id = ?", (review_id,)).fetchone()
        return dict(row) if row else None


def register_company(name, email, username, password_hash):
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO companies(name,email,username,password)
               VALUES(?,?,?,?)""",
            (name.strip(), email.strip().lower(),
             username.strip(), password_hash)
        )
        return cur.lastrowid
        cursor = conn.execute(
            "INSERT INTO companies (name, email, username, password) VALUES (?, ?, ?, ?)",
            (name, email, username, password_hash),
        )
        return cursor.lastrowid


def login_company(username):
    with get_db() as conn:
        row = conn.execute(
            """SELECT * FROM companies
               WHERE username=? OR email=?""",
            (username, username.lower())
        ).fetchone()
        return dict(row) if row else None


def create_tender(title, requirements):
    if isinstance(requirements, (list, dict)):
        requirements = json.dumps(requirements)
    with get_db() as conn:
        cur = conn.execute(
            "INSERT INTO tenders(title,requirements) VALUES(?,?)",
            (title, requirements)
        )
        return cur.lastrowid


def get_all_tenders():
    with get_db() as conn:
        return [dict(r) for r in conn.execute(
            "SELECT * FROM tenders ORDER BY id DESC"
        )]


def save_submission(company_id, filename, extracted_text="",
                    tender_id=None):
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO submissions
               (company_id,tender_id,filename,extracted_text)
               VALUES(?,?,?,?)""",
            (company_id, tender_id, filename, extracted_text)
        )
        return cur.lastrowid


def update_submission_text(submission_id, extracted_text):
    with get_db() as conn:
        cur = conn.execute(
            """UPDATE submissions SET extracted_text=?,status='Extracted'
               WHERE id=?""",
            (extracted_text, submission_id)
        )
        return cur.rowcount > 0


def save_verification_result(submission_id, requirements_checked,
                             matched, missing, score, status,
                             result_summary=""):
    allowed = {"Pending", "Match", "Manual Review", "Mismatch", "Error"}
    if status not in allowed:
        raise ValueError("Invalid verification status")
    if score is not None and not 0 <= float(score) <= 100:
        raise ValueError("Score must be between 0 and 100")

    def encode(value):
        return json.dumps(value) if isinstance(value, (list, dict)) else value

    with get_db() as conn:
        conn.execute(
            """INSERT INTO verification_results
               (submission_id,requirements_checked,matched,missing,
                score,status,result_summary,verified_at)
               VALUES(?,?,?,?,?,?,?,CURRENT_TIMESTAMP)
               ON CONFLICT(submission_id) DO UPDATE SET
                requirements_checked=excluded.requirements_checked,
                matched=excluded.matched, missing=excluded.missing,
                score=excluded.score, status=excluded.status,
                result_summary=excluded.result_summary,
                verified_at=CURRENT_TIMESTAMP""",
            (submission_id, encode(requirements_checked), encode(matched),
             encode(missing), score, status, result_summary)
        )
        conn.execute(
            "UPDATE submissions SET status='Verified' WHERE id=?",
            (submission_id,)
        )


def save_review(filename, requirements, summary,
                company_id=None, submission_id=None):
    if isinstance(requirements, (list, dict)):
        requirements = json.dumps(requirements)
    with get_db() as conn:
        cur = conn.execute(
            """INSERT INTO reviews
               (company_id,submission_id,filename,requirements,
                summary,result_summary)
               VALUES(?,?,?,?,?,?)""",
            (company_id, submission_id, filename, requirements,
             summary, summary)
        )
        return cur.lastrowid


def get_review_by_id(review_id, company_id):
    with get_db() as conn:
        row = conn.execute(
            "SELECT * FROM reviews WHERE id=? AND company_id=?",
            (review_id, company_id)
        ).fetchone()
        return dict(row) if row else None


def get_company_verification_history(company_id):
    with get_db() as conn:
        rows = conn.execute(
            """SELECT s.id AS submission_id, s.filename,
                      s.status AS submission_status, s.uploaded_at,
                      t.title AS tender_title, v.requirements_checked,
                      v.matched, v.missing, v.score,
                      v.status AS verification_status,
                      v.result_summary, v.verified_at
               FROM submissions s
               LEFT JOIN tenders t ON s.tender_id=t.id
               LEFT JOIN verification_results v ON s.id=v.submission_id
               WHERE s.company_id=?
               ORDER BY s.id DESC""",
            (company_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_all_reviews(company_id):
    with get_db() as conn:
        rows = conn.execute(
            "SELECT * FROM reviews WHERE company_id=? ORDER BY id DESC",
            (company_id,)
        ).fetchall()
        return [dict(r) for r in rows]


def get_dashboard_statistics(company_id):
    with get_db() as conn:
        total = conn.execute(
            "SELECT COUNT(*) FROM submissions WHERE company_id=?",
            (company_id,)
        ).fetchone()[0]

        matched = conn.execute(
            """SELECT COUNT(*) FROM submissions s
               JOIN verification_results v ON s.id=v.submission_id
               WHERE s.company_id=? AND v.status='Match'""",
            (company_id,)
        ).fetchone()[0]

        manual = conn.execute(
            """SELECT COUNT(*) FROM submissions s
               JOIN verification_results v ON s.id=v.submission_id
               WHERE s.company_id=? AND v.status='Manual Review'""",
            (company_id,)
        ).fetchone()[0]

        return {
            "total_documents": total,
            "verified_documents": matched,
            "manual_reviews": manual
        }



if __name__ == "__main__":
    initialize_database()
    print("GeM database initialized successfully.")
