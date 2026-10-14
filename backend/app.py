from pathlib import Path
from uuid import uuid4

from flask import Flask, request, jsonify

from backend.extraction import extract_text
from backend.compliance import check_compliance
from backend.database import (
    initialize_database,
    save_review,
    get_all_reviews,
    get_review_by_id,
)

app = Flask(__name__)

# Maximum upload size: 10 MB
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024

# Temporary PDF upload directory
UPLOAD_FOLDER = Path(__file__).resolve().parent / "uploads"
UPLOAD_FOLDER.mkdir(parents=True, exist_ok=True)

# Initialize the SQLite database
initialize_database()


@app.route("/", methods=["GET"])
def home():
    return jsonify({
        "message": "GeM Bid Compliance Verification API is running."
    }), 200


@app.route("/verify", methods=["POST"])
def verify():
    # 1. Check uploaded file
    if "file" not in request.files:
        return jsonify({
            "error": "No PDF file uploaded."
        }), 400

    uploaded_file = request.files["file"]

    if not uploaded_file.filename:
        return jsonify({
            "error": "Please select a PDF file."
        }), 400

    if Path(uploaded_file.filename).suffix.lower() != ".pdf":
        return jsonify({
            "error": "Only PDF files are supported."
        }), 400

    # 2. Read tender requirements
    requirements_text = request.form.get(
        "requirements",
        "GST, PAN, Turnover"
    )

    requirements = [
        item.strip()
        for item in requirements_text.split(",")
        if item.strip()
    ]

    if not requirements:
        return jsonify({
            "error": "Please provide at least one requirement."
        }), 400

    # 3. Save PDF temporarily
    temporary_path = UPLOAD_FOLDER / f"{uuid4().hex}.pdf"

    try:
        uploaded_file.save(temporary_path)

        # 4. Extract PDF text
        extracted_text = extract_text(temporary_path)

        # 5. Check compliance
        result = check_compliance(
            extracted_text,
            requirements
        )

        # 6. Prepare summary for SQLite
        summary = (
            f"Status: {result['status']}; "
            f"Score: {result['score']}%; "
            f"Matched: {len(result['matched_requirements'])}; "
            f"Missing: {len(result['missing_requirements'])}; "
            f"Manual review: {len(result['manual_review'])}"
        )

        # 7. Save verification history
        review_id = save_review(
            uploaded_file.filename,
            ", ".join(requirements),
            summary
        )

        # 8. Return result
        return jsonify({
            "review_id": review_id,
            "filename": uploaded_file.filename,
            "status": result["status"],
            "score": result["score"],
            "matched_requirements": result[
                "matched_requirements"
            ],
            "missing_requirements": result[
                "missing_requirements"
            ],
            "manual_review": result["manual_review"],
            "message": result["message"]
        }), 200

    except (ValueError, FileNotFoundError) as error:
        return jsonify({
            "error": str(error)
        }), 400

    except Exception as error:
        # Log the full error in the Flask terminal
        app.logger.exception("Document verification failed.")

        # Show the error type and message for debugging
        return jsonify({
            "error": str(error),
            "type": type(error).__name__
        }), 500

    finally:
        # Remove the temporary PDF after processing
        if temporary_path.exists():
            temporary_path.unlink()


@app.route("/history", methods=["GET"])
def history():
    return jsonify(get_all_reviews()), 200


@app.route("/history/<int:review_id>", methods=["GET"])
def review_details(review_id):
    review = get_review_by_id(review_id)

    if review is None:
        return jsonify({
            "error": "Verification record not found."
        }), 404

    return jsonify(review), 200


@app.errorhandler(413)
def file_too_large(error):
    return jsonify({
        "error": "The uploaded file exceeds the 10 MB limit."
    }), 413


if __name__ == "__main__":
    app.run(debug=True, port=5000)