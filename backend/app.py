
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


@app.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return jsonify({"message": "Logged out successfully."}), 200


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


@app.route("/history/<int:review_id>", methods=["GET"])
@login_required
def review_details(review_id):
    review = get_review_by_id(review_id, session["company_id"])

    if review is None:
        return jsonify({
            "error": "Verification record not found."
        }), 404

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


if __name__ == "__main__":
    app.run(debug=True, port=5000)
