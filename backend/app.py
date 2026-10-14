
import os
import sys
from pathlib import Path
from uuid import uuid4
from functools import wraps

from flask import Flask, request, jsonify, session
from werkzeug.security import generate_password_hash, check_password_hash

# Fix imports when running from the project root
BASE_DIR = Path(__file__).resolve().parent
sys.path.insert(0, str(BASE_DIR))

from extraction import extract_text
from compliance import check_compliance
from database import (
    initialize_database,
    register_company,
    login_company,
    save_submission,
    update_submission_text,
    save_verification_result,
    save_review,
    get_all_reviews,
    get_review_by_id,
    get_company_verification_history,
    get_dashboard_statistics,
)

app = Flask(__name__)
app.secret_key = os.environ.get(
    "FLASK_SECRET_KEY", "change-this-secret-before-deployment"
)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

UPLOAD_FOLDER = BASE_DIR / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

initialize_database()


# --------------------------------------------------
# HELPER FUNCTIONS
# --------------------------------------------------

def login_required(function):
    @wraps(function)
    def wrapper(*args, **kwargs):
        if "company_id" not in session:
            return jsonify({"error": "Please log in first."}), 401
        return function(*args, **kwargs)
    return wrapper


def input_value(name, default=""):
    data = request.get_json(silent=True) or {}
    return request.form.get(name, data.get(name, default))


# --------------------------------------------------
# HOME
# --------------------------------------------------

@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "GeM Bid Compliance Verification API is running.",
        "features": [
            "Company registration and login",
            "PDF upload and text extraction",
            "Bid compliance checking",
            "SQLite result storage",
            "Company-specific verification history",
        ],
    }), 200
import os
import secrets
import sqlite3

from flask import Flask, request, jsonify
from flask_cors import CORS
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename

from backend.extraction import extract_text
from backend.compliance import check_compliance
from backend.database import (
    initialize_database, save_review, get_all_reviews, get_review_by_id,
    register_company, login_company, get_db, DB_NAME
)

app = Flask(__name__)
CORS(
    app,
    resources={r"/*": {"origins": [
        "http://127.0.0.1:5500",
        "http://localhost:5500"
    ]}},
    allow_headers=["Content-Type", "Authorization"],
    methods=["GET", "POST", "OPTIONS"]
)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024
UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Development-only in-memory tokens. For production, use a proper session/JWT setup.
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
    if not user:
        return None
    if required_role and user.get("role") != required_role:
        return None
    return user


def issue_token(user):
    token = secrets.token_urlsafe(32)
    TOKENS[token] = user
    return token


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "GeM Bid Compliance Verification API is running."}), 200


@app.route("/auth/company/register", methods=["POST"])
def company_register():
    data = request.get_json(silent=True) or {}
    name = str(data.get("name", "")).strip()
    email = str(data.get("email", "")).strip().lower()
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))

    if not all([name, email, username, password]):
        return error("Name, email, username and password are required.")
    if "@" not in email or "." not in email.rsplit("@", 1)[-1]:
        return error("Enter a valid email address.")
    if len(password) < 8:
        return error("Password must contain at least 8 characters.")

    try:
        company_id = register_company(name, email, username, generate_password_hash(password))
    except sqlite3.IntegrityError:
        return error("That username or email is already registered.", 409)
    except Exception:
        app.logger.exception("Company registration failed")
        return error("Could not create the company account.", 500)

    token = issue_token({"role": "company", "company_id": company_id, "name": name, "username": username})
    return jsonify({"message": "Company account created.", "token": token, "role": "company",
                    "company": {"id": company_id, "name": name, "username": username}}), 201


@app.route("/auth/company/login", methods=["POST"])
def company_login():
    data = request.get_json(silent=True) or {}
    username = str(data.get("username", "")).strip()
    password = str(data.get("password", ""))
    if not username or not password:
        return error("Username/email and password are required.")
    company = login_company(username)
    if not company or not check_password_hash(company["password"], password):
        return error("Invalid username/email or password.", 401)
    token = issue_token({"role": "company", "company_id": company["id"],
                         "name": company["name"], "username": company["username"]})
    return jsonify({"message": "Login successful.", "token": token, "role": "company",
                    "company": {"id": company["id"], "name": company["name"],
                                "username": company["username"]}}), 200


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
    return jsonify({"message": "Logged out."}), 200


# --------------------------------------------------
# COMPANY REGISTRATION
# --------------------------------------------------

@app.route("/register", methods=["POST"])
def register():
    name = input_value("name").strip()
    email = input_value("email").strip().lower()
    username = input_value("username").strip()
    password = input_value("password")

    if not all([name, email, username, password]):
        return jsonify({"error": "All fields are required."}), 400

    if len(password) < 8:
        return jsonify({
            "error": "Password must contain at least 8 characters."
        }), 400

    try:
        company_id = register_company(
            name,
            email,
            username,
            generate_password_hash(password),
        )
        return jsonify({
            "message": "Company registered successfully.",
            "company_id": company_id,
        }), 201

    except Exception as error:
        if "UNIQUE constraint failed" in str(error):
            return jsonify({
                "error": "Email or username already exists."
            }), 409

        app.logger.exception("Company registration failed.")
        return jsonify({"error": "Registration failed."}), 500


# --------------------------------------------------
# COMPANY LOGIN
# --------------------------------------------------

@app.route("/login", methods=["POST"])
def login():
    username = input_value("username").strip()
    password = input_value("password")

    if not username or not password:
        return jsonify({
            "error": "Username/email and password are required."
        }), 400

    company = login_company(username)

    if not company or not check_password_hash(
        company["password"], password
    ):
        return jsonify({
            "error": "Invalid username/email or password."
        }), 401

    session.clear()
    session["company_id"] = company["id"]
    session["company_name"] = company["name"]

    return jsonify({
        "message": "Login successful.",
        "company_id": company["id"],
        "company_name": company["name"],
    }), 200




# --------------------------------------------------
# PDF UPLOAD AND COMPLIANCE VERIFICATION
# --------------------------------------------------

@app.route("/verify", methods=["POST"])
@login_required
def verify():
    uploaded_file = request.files.get("file")

    if not uploaded_file or not uploaded_file.filename:
        return jsonify({"error": "Please upload a PDF file."}), 400

    if Path(uploaded_file.filename).suffix.lower() != ".pdf":
        return jsonify({"error": "Only PDF files are supported."}), 400

    requirements_text = input_value(
        "requirements", "GST, PAN, Turnover"
    ).strip()

    requirements = [
        item.strip()
        for item in requirements_text.replace("\n", ",").split(",")
        if item.strip()
    ]

    if not requirements:
        return jsonify({
            "error": "Please provide at least one requirement."
        }), 400

    original_filename = Path(uploaded_file.filename).name
    temporary_path = UPLOAD_FOLDER / f"{uuid4().hex}.pdf"
    submission_id = None

    try:
        uploaded_file.save(str(temporary_path))

        # Save submission under the logged-in company.
        submission_id = save_submission(
            company_id=session["company_id"],
            filename=original_filename,
            extracted_text="",
        )

        # Extract text from the uploaded PDF.
        extracted_text = extract_text(temporary_path)

        if not isinstance(extracted_text, str) or not extracted_text.strip():
            update_submission_text(submission_id, "")
            save_verification_result(
                submission_id,
                requirements,
                [],
                requirements,
                0,
                "Manual Review",
                "No readable PDF text was extracted. Manual review is required.",
            )
            return jsonify({
                "submission_id": submission_id,
                "filename": original_filename,
                "status": "Manual Review",
                "message": "No readable text found. The PDF may be scanned or empty.",
            }), 200

        update_submission_text(submission_id, extracted_text)

        # Run the existing compliance module.
        result = check_compliance(extracted_text, requirements)

        matched = result["matched_requirements"]
        missing = result["missing_requirements"]
        manual = result["manual_review"]
        score = result["score"]
        status = result["status"]

        # Normalize status for the database.
        allowed_statuses = {
            "Pending", "Match", "Manual Review", "Mismatch", "Error"
        }

        if status not in allowed_statuses:
            if manual:
                status = "Manual Review"
            elif missing:
                status = "Mismatch"
            else:
                status = "Match"

        summary = (
            f"Status: {status}; Score: {score}%; "
            f"Matched: {len(matched)}; Missing: {len(missing)}; "
            f"Manual review: {len(manual)}"
        )

        # Save detailed verification results.
        save_verification_result(
            submission_id,
            requirements,
            matched,
            missing,
            score,
            status,
            result.get("message", summary),
        )

        # Save the summary for the review history.
        review_id = save_review(
            original_filename,
            ", ".join(requirements),
            summary,
            company_id=session["company_id"],
            submission_id=submission_id,
        )

        return jsonify({
            "review_id": review_id,
            "submission_id": submission_id,
            "filename": original_filename,
            "status": status,
            "score": score,
            "matched_requirements": matched,
            "missing_requirements": missing,
            "manual_review": manual,
            "message": result.get("message", summary),
        }), 200

    except (ValueError, FileNotFoundError) as error:
        app.logger.warning("Verification input error: %s", error)
        return jsonify({"error": str(error)}), 400

    except Exception:
        app.logger.exception("Document verification failed.")
        return jsonify({
            "error": "Verification failed. Check the Flask terminal for details."
        }), 500

    # Legacy endpoint retained for compatibility; role-protected routes below should be used by the UI.
    if "file" not in request.files:
        return error("No PDF file uploaded.")
    uploaded_file = request.files["file"]
    if not uploaded_file.filename:
        return error("Please select a PDF file.")
    if Path(uploaded_file.filename).suffix.lower() != ".pdf":
        return error("Only PDF files are supported.")
    requirements_text = request.form.get("requirements", "GST, PAN, Turnover")
    requirements = [item.strip() for item in requirements_text.split(",") if item.strip()]
    if not requirements:
        return error("Please provide at least one requirement.")
    temporary_path = UPLOAD_FOLDER / f"{uuid4().hex}.pdf"
    try:
        uploaded_file.save(temporary_path)
        extracted_text = extract_text(temporary_path)
        result = check_compliance(extracted_text, requirements)
        summary = (f"Status: {result['status']}; Score: {result['score']}%; "
                   f"Matched: {len(result['matched_requirements'])}; "
                   f"Missing: {len(result['missing_requirements'])}; "
                   f"Manual review: {len(result['manual_review'])}")
        review_id = save_review(secure_filename(uploaded_file.filename), ", ".join(requirements), summary)
        return jsonify({"review_id": review_id, "filename": secure_filename(uploaded_file.filename),
                        "status": result["status"], "score": result["score"],
                        "matched_requirements": result["matched_requirements"],
                        "missing_requirements": result["missing_requirements"],
                        "manual_review": result["manual_review"], "message": result["message"]}), 200
    except (ValueError, FileNotFoundError) as exc:
        return error(str(exc))
    except Exception as exc:
        app.logger.exception("Document verification failed.")
        return jsonify({"error": str(exc), "type": type(exc).__name__}), 500
    finally:
        if temporary_path.exists():
            temporary_path.unlink()


# --------------------------------------------------
# VERIFICATION HISTORY
# --------------------------------------------------

@app.route("/history", methods=["GET"])
@login_required
def history():
    records = get_company_verification_history(session["company_id"])
    return jsonify(records), 200
    # Legacy history is now admin-only to prevent public disclosure.
    if not current_user("admin"):
        return error("Government administrator access required.", 401)
    return jsonify(get_all_reviews()), 200


@app.route("/history/<int:review_id>", methods=["GET"])
@login_required
def review_details(review_id):
    review = get_review_by_id(review_id, session["company_id"])

    if not current_user("admin"):
        return error("Government administrator access required.", 401)
    review = get_review_by_id(review_id)
    if review is None:
        return error("Verification record not found.", 404)
    return jsonify(review), 200


# --------------------------------------------------
# DASHBOARD STATISTICS
# --------------------------------------------------

@app.route("/dashboard", methods=["GET"])
@login_required
def dashboard():
    statistics = get_dashboard_statistics(session["company_id"])
    return jsonify(statistics), 200


# --------------------------------------------------
# ERROR HANDLERS
# --------------------------------------------------

@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "PDF exceeds the 10 MB upload limit."
    }), 413
@app.route("/tenders", methods=["GET"])
def public_tenders():
    user = current_user("company")
    if not user:
        return error("Company login required.", 401)
    with get_db() as conn:
        rows = conn.execute("SELECT id, title, requirements FROM tenders ORDER BY id DESC").fetchall()
    return jsonify([dict(row) for row in rows]), 200


@app.route("/admin/tenders", methods=["GET", "POST"])
def admin_tenders():
    if not current_user("admin"):
        return error("Government administrator access required.", 401)
    if request.method == "GET":
        with get_db() as conn:
            rows = conn.execute("SELECT id, title, requirements FROM tenders ORDER BY id DESC").fetchall()
        return jsonify([dict(row) for row in rows]), 200
    data = request.get_json(silent=True) or {}
    title = str(data.get("title", "")).strip()
    requirements = data.get("requirements", [])
    if isinstance(requirements, str):
        requirements = [x.strip() for x in requirements.split(",") if x.strip()]
    if not title or not isinstance(requirements, list) or not requirements:
        return error("Tender title and at least one requirement are required.")
    with get_db() as conn:
        cursor = conn.execute("INSERT INTO tenders (title, requirements) VALUES (?, ?)",
                              (title, ", ".join(str(x).strip() for x in requirements if str(x).strip())))
        tender_id = cursor.lastrowid
    return jsonify({"id": tender_id, "title": title, "requirements": requirements}), 201


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
            (tender_id,)
        ).fetchone()

    if not tender:
        return error("Tender not found.", 404)

    path = UPLOAD_FOLDER / f"{uuid4().hex}.pdf"

    try:
        upload.save(path)
        extracted = extract_text(path)
        requirements = [
            item.strip()
            for item in tender["requirements"].split(",")
            if item.strip()
        ]

        result = check_compliance(extracted, requirements)

        # Temporary diagnostics: these appear in the backend terminal.
        print("TENDER REQUIREMENTS:", requirements)
        print("EXTRACTED TEXT:", repr(extracted[:1000]))
        print("COMPLIANCE RESULT:", result)

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
                "Submitted"
            ))
            submission_id = cursor.lastrowid

            conn.execute("""
                INSERT INTO verification_results
                    (submission_id, matched, missing, score, status)
                VALUES (?, ?, ?, ?, ?)
            """, (
                submission_id,
                ", ".join(result["matched_requirements"]),
                ", ".join(result["missing_requirements"]),
                result["score"],
                result["status"]
            ))

        # Detailed compliance results are shown only in the government workspace.
        return jsonify({
            "message": "Bid submitted successfully for government review.",
            "submission_id": submission_id,
            "status": "Submitted"
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

    print("ADMIN RESULTS FROM DATABASE:", [dict(row) for row in rows])
    return jsonify([dict(row) for row in rows]), 200


@app.errorhandler(413)
def file_too_large(exc):
    return error("The uploaded file exceeds the 10 MB limit.", 413)


if __name__ == "__main__":
    app.run(debug=True, port=5000)
