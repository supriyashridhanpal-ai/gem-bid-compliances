import json
import logging
import os
import re
import secrets
import sqlite3
import subprocess
import sys
from functools import wraps
from pathlib import Path
from uuid import uuid4

from flask import Flask, jsonify, request, session
from flask_cors import CORS
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename

CURRENT_DIR = Path(__file__).resolve().parent
PROJECT_ROOT = CURRENT_DIR.parent
for directory in (str(CURRENT_DIR), str(PROJECT_ROOT)):
    if directory not in sys.path:
        sys.path.insert(0, directory)

from extraction import extract_text
from compliance import check_compliance
from database import (
    initialize_database,
    save_review,
    get_all_reviews,
    get_review_by_id,
    register_company,
    login_company,
    get_db,
    save_submission,
    update_submission_text,
    save_verification_result,
    get_company_verification_history,
    get_dashboard_statistics,
)

app = Flask(__name__)
# Silence Werkzeug HTTP request logs in terminal
logging.getLogger("werkzeug").setLevel(logging.ERROR)

app.secret_key = os.environ.get("FLASK_SECRET_KEY", "gem-bid-compliance-secure-key-2026")
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

CORS(
    app,
    resources={r"/*": {"origins": ["http://127.0.0.1:5500", "http://localhost:5500", "*"]}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "DELETE", "OPTIONS"],
)

UPLOAD_FOLDER = CURRENT_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

TOKENS = {}
ADMIN_USERNAME = os.environ.get("GEM_ADMIN_USERNAME", "Goverment")
ADMIN_PASSWORD = os.environ.get("GEM_ADMIN_PASSWORD", "1234567890")

initialize_database()


def error(message, status=400):
    return jsonify({"error": message}), status


def current_user(required_role=None):
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
    user = TOKENS.get(token)

    if not user and "company_id" in session:
        user = {
            "role": "company",
            "company_id": session.get("company_id"),
            "name": session.get("company_name", "Company"),
            "username": session.get("company_name", "Company"),
        }

    if not user:
        return None
    if required_role and user.get("role") != required_role:
        return None
    return user


def issue_token(user):
    token = secrets.token_urlsafe(32)
    TOKENS[token] = user
    return token


def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        user = current_user("company")
        if not user:
            return error("Please log in first.", 401)
        return function(*args, **kwargs)
    return wrapper


def input_value(name, default=""):
    data = request.get_json(silent=True) or {}
    return request.form.get(name, data.get(name, default))


def get_tender_budget(row):
    """
    Extracts the exact budget assigned to a tender.
    Returns clean fixed default (50) instead of random numbers if not set.
    """
    text = f"{row['title']} {row['requirements']}"

    # 1. Match explicit "Budget: 50" or "Budget: 50 Lakhs"
    match = re.search(r"budget[:\s]*(\d+)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # 2. Match numbers attached to Lakhs (e.g. "50 Lakhs", "50L", "Turnover 50L")
    match = re.search(r"(\d+)\s*(?:lakhs?|l\b)", text, re.IGNORECASE)
    if match:
        return int(match.group(1))

    # 3. Match any standalone number between 10 and 500 (avoiding year 2026)
    numbers = re.findall(r"\b(\d+)\b", text)
    for n in numbers:
        val = int(n)
        if 10 <= val <= 500 and val != 2026:
            return val

    # Clean default: 50 Lakhs
    return 50


# --------------------------------------------------
# SYSTEM STATUS
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "GeM Bid Compliance Verification API with C DS Engine is running.",
        "status": "Online",
        "data_structures": [
            "1. Singly Linked List (Tender Nodes & Dynamic Deletion)",
            "2. Queue (FIFO Vendor Bid Processing Pipeline)",
            "3. Binary Search Tree (Tender Budget Range Search)",
            "4. Priority Queue / Binary Max-Heap (L1/H1 Per-Tender Leaderboard)",
            "5. Hashing (Exemption Lookup)",
            "6. Graph (BFS & DFS Pipeline Validation)",
        ],
    }), 200


# --------------------------------------------------
# AUTHENTICATION ROUTES
# --------------------------------------------------

@app.route("/auth/company/register", methods=["POST"])
@app.route("/register", methods=["POST"])
def company_register():
    data = request.get_json(silent=True) or {}
    name = str(request.form.get("name", data.get("name", ""))).strip()
    email = str(request.form.get("email", data.get("email", ""))).strip().lower()
    username = str(request.form.get("username", data.get("username", ""))).strip()
    password = str(request.form.get("password", data.get("password", "")))

    if not all([name, email, username, password]):
        return error("Name, email, username, and password are required.")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return error("Enter a valid email address.")
    if len(password) < 8:
        return error("Password must contain at least 8 characters.")

    try:
        company_id = register_company(name, email, username, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return error("That username or email is already registered.", 409)
    except Exception as exc:
        app.logger.exception("Company registration failed: %s", exc)
        return error("Could not create the company account.", 500)

    token = issue_token({"role": "company", "company_id": company_id, "name": name, "username": username})
    session["company_id"] = company_id
    session["company_name"] = name

    return jsonify({
        "message": "Company registered successfully.",
        "token": token,
        "role": "company",
        "company": {"id": company_id, "name": name, "username": username},
    }), 201


@app.route("/auth/company/login", methods=["POST"])
@app.route("/login", methods=["POST"])
def company_login():
    data = request.get_json(silent=True) or {}
    username = str(request.form.get("username", data.get("username", ""))).strip()
    password = str(request.form.get("password", data.get("password", "")))

    if not username or not password:
        return error("Username/email and password are required.")

    company = login_company(username)
    if not company or not check_password_hash(company["password"], password):
        return error("Invalid username/email or password.", 401)

    token = issue_token({
        "role": "company",
        "company_id": company["id"],
        "name": company["name"],
        "username": company["username"],
    })
    session["company_id"] = company["id"]
    session["company_name"] = company["name"]

    return jsonify({
        "message": "Login successful.",
        "token": token,
        "role": "company",
        "company": {"id": company["id"], "name": company["name"], "username": company["username"]},
    }), 200


@app.route("/auth/admin/login", methods=["POST"])
def admin_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if secrets.compare_digest(username, ADMIN_USERNAME) and secrets.compare_digest(password, ADMIN_PASSWORD):
        token = issue_token({"role": "admin", "name": "Government Administrator"})
        return jsonify({"message": "Login successful.", "token": token, "role": "admin"}), 200

    return error("Invalid government administrator credentials.", 401)


@app.route("/auth/logout", methods=["POST"])
def logout():
    header = request.headers.get("Authorization", "")
    token = header.removeprefix("Bearer ").strip() if header.startswith("Bearer ") else ""
    TOKENS.pop(token, None)
    session.clear()
    return jsonify({"message": "Logged out."}), 200


# --------------------------------------------------
# TENDERS & C ENGINE OPERATIONS
# --------------------------------------------------

@app.route("/tenders", methods=["GET"])
def public_tenders():
    user = current_user("company")
    if not user:
        return error("Company login required.", 401)
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, requirements FROM tenders ORDER BY id DESC").fetchall()

    result = []
    for r in rows:
        d = dict(r)
        d["budget"] = get_tender_budget(r)
        result.append(d)
    return jsonify(result), 200


@app.route("/tenders/filter", methods=["GET"])
def filter_tenders_bst():
    """
    Filters tenders using Binary Search Tree (BST) In-Order Range Search in C.
    """
    user = current_user("company")
    if not user:
        return error("Company login required.", 401)

    min_budget = request.args.get("min", default=0, type=int)
    max_budget = request.args.get("max", default=500, type=int)

    with get_db() as conn:
        rows = conn.execute("SELECT id, title, requirements FROM tenders").fetchall()

    if not rows:
        return jsonify([]), 200

    serialized_bst = ";;".join(
        f"{r['id']}|{r['title']}|{r['requirements']}|{get_tender_budget(r)}"
        for r in rows
    )

    c_engine_path = CURRENT_DIR.parent / "c_engine" / "gem_ds.exe"

    try:
        c_proc = subprocess.run(
            [str(c_engine_path), "filter_bst", str(min_budget), str(max_budget), serialized_bst],
            capture_output=True,
            text=True,
            check=True,
        )
        c_output = json.loads(c_proc.stdout.strip())
        return jsonify(c_output.get("tenders", [])), 200
    except Exception as exc:
        app.logger.exception("C BST filtering failed: %s", exc)
        return error(f"C BST Filter failed: {str(exc)}", 500)


@app.route("/admin/tenders", methods=["GET", "POST"])
def admin_tenders():
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute("SELECT id, title, requirements FROM tenders ORDER BY id DESC").fetchall()
        result = []
        for r in rows:
            d = dict(r)
            d["budget"] = get_tender_budget(r)
            result.append(d)
        return jsonify(result), 200

    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    requirements = data.get("requirements", [])
    budget = data.get("budget")

    if isinstance(requirements, str):
        requirements = [x.strip() for x in requirements.split(",") if x.strip()]

    # Save explicit budget if provided
    if budget:
        requirements.insert(0, f"Budget: {budget} Lakhs")

    if not title or not isinstance(requirements, list) or not requirements:
        return error("Tender title and at least one requirement are required.")

    req_str = ", ".join(str(x).strip() for x in requirements if str(x).strip())

    with get_db() as conn:
        cursor = conn.execute(
            "INSERT INTO tenders (title, requirements) VALUES (?, ?)",
            (title, req_str),
        )
        tender_id = cursor.lastrowid

    return jsonify({"id": tender_id, "title": title, "requirements": requirements}), 201


@app.route("/admin/tenders/<int:tender_id>", methods=["DELETE"])
def admin_delete_tender(tender_id):
    """
    Deletes a tender by executing Singly Linked List pointer unlinking in C (gem_ds.exe).
    """
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    with get_db() as conn:
        rows = conn.execute("SELECT id, title, requirements FROM tenders").fetchall()

    if not rows:
        return error("No tenders available to delete.", 404)

    serialized_tenders = ";;".join(
        f"{r['id']}|{r['title']}|{r['requirements']}" for r in rows
    )

    c_engine_path = CURRENT_DIR.parent / "c_engine" / "gem_ds.exe"

    try:
        c_proc = subprocess.run(
            [str(c_engine_path), "delete_tender", str(tender_id), serialized_tenders],
            capture_output=True,
            text=True,
            check=True,
        )
        c_output = json.loads(c_proc.stdout.strip())

        if c_output.get("status") == "SUCCESS":
            with get_db() as conn:
                conn.execute("DELETE FROM tenders WHERE id = ?", (tender_id,))

            return jsonify({
                "message": f"Tender #{tender_id} deleted successfully.",
                "ds_engine": c_output,
            }), 200
        else:
            return error(f"Tender #{tender_id} node not found in C Linked List.", 404)

    except Exception as exc:
        app.logger.exception("C Engine tender deletion failed: %s", exc)
        return error(f"C Linked List operation failed: {str(exc)}", 500)


# --------------------------------------------------
# CONCEPT 2: FIFO BID PROCESSING QUEUE
# --------------------------------------------------

@app.route("/admin/queue/process_next", methods=["POST"])
def admin_process_next_queue():
    """
    Dequeues the oldest pending bid submission using C Linked Queue (FIFO)
    and executes the compliance verification engine to produce its official result.
    """
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    with get_db() as conn:
        pending_rows = conn.execute("""
            SELECT s.id, c.name AS company_name, COALESCE(t.title, 'General Tender') AS tender_title,
                   s.extracted_text, t.requirements
            FROM submissions s
            JOIN companies c ON c.id = s.company_id
            LEFT JOIN tenders t ON t.id = s.tender_id
            WHERE s.status IN ('Queued', 'Submitted')
            ORDER BY s.id ASC
        """).fetchall()

    if not pending_rows:
        return jsonify({
            "message": "The bid queue is currently empty. No pending submissions to evaluate.",
            "status": "EMPTY",
            "remaining_in_queue": 0,
        }), 200

    serialized_queue = ";;".join(
        f"{r['id']}|{r['company_name']}|{r['tender_title']}" for r in pending_rows
    )

    c_engine_path = CURRENT_DIR.parent / "c_engine" / "gem_ds.exe"

    try:
        c_proc = subprocess.run(
            [str(c_engine_path), "process_queue", serialized_queue],
            capture_output=True,
            text=True,
            check=True,
        )
        c_output = json.loads(c_proc.stdout.strip())

        if c_output.get("status") == "SUCCESS":
            dequeued_id = c_output["dequeued_id"]
            target_sub = next((r for r in pending_rows if r["id"] == dequeued_id), None)

            if target_sub:
                extracted = target_sub["extracted_text"] or ""
                requirements = [
                    item.strip()
                    for item in (target_sub["requirements"] or "GST, PAN, Turnover").split(",")
                    if item.strip()
                ]

                eval_result = check_compliance(extracted, requirements)

                with get_db() as conn:
                    existing = conn.execute(
                        "SELECT id FROM verification_results WHERE submission_id = ?",
                        (dequeued_id,),
                    ).fetchone()
                    if existing:
                        conn.execute("""
                            UPDATE verification_results
                            SET matched = ?, missing = ?, score = ?, status = ?
                            WHERE submission_id = ?
                        """, (
                            ", ".join(eval_result["matched_requirements"]),
                            ", ".join(eval_result["missing_requirements"]),
                            eval_result["score"],
                            eval_result["status"],
                            dequeued_id,
                        ))
                    else:
                        conn.execute("""
                            INSERT INTO verification_results
                                (submission_id, matched, missing, score, status)
                            VALUES (?, ?, ?, ?, ?)
                        """, (
                            dequeued_id,
                            ", ".join(eval_result["matched_requirements"]),
                            ", ".join(eval_result["missing_requirements"]),
                            eval_result["score"],
                            eval_result["status"],
                        ))

                    conn.execute(
                        "UPDATE submissions SET status = 'Reviewed' WHERE id = ?",
                        (dequeued_id,),
                    )

                return jsonify({
                    "message": f"Dequeued & Evaluated Submission #{dequeued_id} ({c_output['company_name']}) in FIFO order: {eval_result['status']} ({eval_result['score']}%)",
                    "ds_engine": c_output,
                    "evaluation": eval_result,
                }), 200

        return jsonify({"message": "No pending submissions in queue.", "status": "EMPTY"}), 200

    except Exception as exc:
        app.logger.exception("C Queue processing failed: %s", exc)
        return error(f"C Queue execution failed: {str(exc)}", 500)


# --------------------------------------------------
# LEADERBOARD (PER-TENDER MAX-HEAP RANKING)
# --------------------------------------------------

@app.route("/admin/leaderboard", methods=["GET"])
def admin_leaderboard_heap():
    """
    Ranks verified bids per tender from high to low using Binary Max-Heap in C.
    """
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    with get_db() as conn:
        all_submissions = conn.execute("""
            SELECT s.id, s.tender_id, c.name AS company_name,
                   COALESCE(t.title, 'General Procurement') AS tender_title,
                   COALESCE(vr.score, 0) AS score
            FROM submissions s
            JOIN companies c ON c.id = s.company_id
            LEFT JOIN tenders t ON t.id = s.tender_id
            JOIN verification_results vr ON vr.submission_id = s.id
            WHERE s.status = 'Reviewed'
            ORDER BY s.id DESC
        """).fetchall()

    if not all_submissions:
        return jsonify({"status": "SUCCESS", "tender_leaderboards": []}), 200

    tender_map = {}
    for r in all_submissions:
        t_id = r["tender_id"] or 0
        if t_id not in tender_map:
            tender_map[t_id] = {
                "tender_id": t_id,
                "tender_title": r["tender_title"],
                "submissions": [],
            }
        tender_map[t_id]["submissions"].append(r)

    c_engine_path = CURRENT_DIR.parent / "c_engine" / "gem_ds.exe"
    tender_leaderboards = []

    for t_id, t_data in tender_map.items():
        subs = t_data["submissions"]
        serialized_heap = ";;".join(
            f"{s['id']}|{s['company_name']}|{s['tender_title']}|{int(s['score'])}"
            for s in subs
        )

        try:
            c_proc = subprocess.run(
                [str(c_engine_path), "leaderboard_heap", serialized_heap],
                capture_output=True,
                text=True,
                check=True,
            )
            c_output = json.loads(c_proc.stdout.strip())
            ranked = c_output.get("leaderboard", [])
        except Exception as e:
            app.logger.warning("C Max-heap failed: %s. Using Python fallback.", e)
            sorted_subs = sorted(subs, key=lambda x: x["score"], reverse=True)
            ranked = [
                {
                    "rank": idx + 1,
                    "submission_id": item["id"],
                    "company_name": item["company_name"],
                    "tender_title": item["tender_title"],
                    "score": item["score"],
                }
                for idx, item in enumerate(sorted_subs)
            ]

        tender_leaderboards.append({
            "tender_id": t_id,
            "tender_title": t_data["tender_title"],
            "total_bids": len(subs),
            "leaderboard": ranked,
        })

    return jsonify({"status": "SUCCESS", "tender_leaderboards": tender_leaderboards}), 200


# --------------------------------------------------
# RESET FEATURES
# --------------------------------------------------

@app.route("/admin/reset", methods=["POST", "DELETE"])
def admin_reset_all():
    """
    Clears all test submissions, queue items, and verification results across the system.
    """
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    with get_db() as conn:
        conn.execute("DELETE FROM verification_results")
        conn.execute("DELETE FROM submissions")
        conn.execute("DELETE FROM reviews")

    return jsonify({"message": "Admin dashboard, bid queue, and submissions reset successfully."}), 200


@app.route("/company/submissions/reset", methods=["POST", "DELETE"])
def company_reset_submissions():
    """
    Clears test submissions for the currently logged-in company.
    """
    user = current_user("company")
    if not user:
        return error("Company login required.", 401)

    company_id = user["company_id"]
    with get_db() as conn:
        sub_rows = conn.execute("SELECT id FROM submissions WHERE company_id = ?", (company_id,)).fetchall()
        sub_ids = [r["id"] for r in sub_rows]
        if sub_ids:
            placeholders = ",".join("?" * len(sub_ids))
            conn.execute(f"DELETE FROM verification_results WHERE submission_id IN ({placeholders})", sub_ids)
            conn.execute("DELETE FROM submissions WHERE company_id = ?", (company_id,))
            conn.execute("DELETE FROM reviews WHERE company_id = ?", (company_id,))

    return jsonify({"message": "Your company submissions and results have been reset."}), 200


# --------------------------------------------------
# SUBMISSIONS & COMPLIANCE
# --------------------------------------------------

@app.route("/company/submissions", methods=["GET", "POST"])
def company_submissions():
    user = current_user("company")
    if not user:
        return error("Company login required.", 401)

    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute("""
                SELECT s.id, s.tender_id, t.title AS tender_title, s.filename, s.status
                FROM submissions s
                LEFT JOIN tenders t ON t.id = s.tender_id
                WHERE s.company_id = ?
                ORDER BY s.id DESC
            """, (user["company_id"],)).fetchall()
        return jsonify([dict(row) for row in rows]), 200

    if "file" not in request.files:
        return error("No PDF file uploaded.")

    upload = request.files["file"]
    if not upload.filename or Path(upload.filename).suffix.lower() != ".pdf":
        return error("Select a valid PDF file.")

    tender_id = request.form.get("tender_id", type=int)
    if not tender_id:
        return error("Select a tender.")

    with get_db() as conn:
        tender = conn.execute(
            "SELECT id, title, requirements FROM tenders WHERE id = ?",
            (tender_id,),
        ).fetchone()

    if not tender:
        return error("Tender not found.", 404)

    path = UPLOAD_FOLDER / f"{uuid4().hex}.pdf"

    try:
        upload.save(path)
        extracted = extract_text(path)

        with get_db() as conn:
            cursor = conn.execute("""
                INSERT INTO submissions
                    (company_id, tender_id, filename, extracted_text, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                user["company_id"],
                tender_id,
                secure_filename(upload.filename),
                extracted,
                "Queued",
            ))
            submission_id = cursor.lastrowid

        return jsonify({
            "message": "Bid submitted successfully and placed in evaluation queue (FIFO).",
            "submission_id": submission_id,
            "status": "Queued",
        }), 201

    except (ValueError, FileNotFoundError) as exc:
        return error(str(exc))
    except Exception as exc:
        app.logger.exception("Submission processing failed.")
        return jsonify({"error": str(exc)}), 500
    finally:
        if path.exists():
            path.unlink()


@app.route("/admin/results", methods=["GET"])
def admin_results():
    """
    Returns administrative review records with dynamic, meaningful compliance details.
    """
    if not current_user("admin"):
        return error("Government administrator access required.", 401)

    with get_db() as conn:
        rows = conn.execute("""
            SELECT s.id AS submission_id, s.company_id, c.name AS company_name,
                   c.username, t.title AS tender_title, s.filename,
                   s.status AS submission_status,
                   vr.matched, vr.missing, vr.score,
                   vr.status AS compliance_status
            FROM submissions s
            JOIN companies c ON c.id = s.company_id
            LEFT JOIN tenders t ON t.id = s.tender_id
            LEFT JOIN verification_results vr ON vr.submission_id = s.id
            ORDER BY s.id DESC
        """).fetchall()

    results = []
    for r in rows:
        d = dict(r)
        sub_status = d.get("submission_status")
        comp_status = (d.get("compliance_status") or "").upper()
        matched = (d.get("matched") or "").strip()
        missing = (d.get("missing") or "").strip()

        if sub_status in ("Queued", "Submitted") and not comp_status:
            d["compliance_status"] = "QUEUED"
            d["score"] = None
            d["details"] = "Waiting in FIFO queue for admin evaluation."
        elif comp_status == "VERIFIED":
            d["details"] = f"All requirements satisfied: {matched}" if matched else "Full compliance criteria satisfied."
        elif comp_status == "NON_COMPLIANT":
            d["details"] = f"Failed mandatory criteria: {missing}" if missing else "Document failed required specifications."
        elif comp_status == "MANUAL_REVIEW":
            d["details"] = "Image-based or unreadable document. Text inspection required."
        else:
            d["details"] = f"Matched: {matched}" if matched else "Evaluation complete."

        results.append(d)

    return jsonify(results), 200


@app.errorhandler(413)
def file_too_large(exc):
    return error("The uploaded file exceeds the 10 MB limit.", 413)


if __name__ == "__main__":
    app.run(debug=True, port=5000)