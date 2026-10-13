from flask import Flask, request, jsonify
from flask_cors import CORS
from backend.extraction import extract_text
from backend.compliance import check_tender_rules
from backend import database

app = Flask(__name__)
CORS(app)

# Create the database table when the server starts
database.initialize_database()


@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server is running!"})


@app.route("/verify", methods=["POST"])
def verify():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400

    file = request.files["file"]

    if not file.filename:
        return jsonify({"error": "No file selected"}), 400

    text = extract_text(file)
    result = check_tender_rules(text)

    # Save the verification result in SQLite
    database.save_review(
        file.filename,
        "Tender rule verification",
        f"Status: {result['status']}; Score: {result['score']}"
    )

    return jsonify({
        "filename": file.filename,
        "status": result["status"],
        "score": result["score"]
    })


@app.route("/history", methods=["GET"])
def history():
    # Retrieve saved verification records
    reviews = database.get_all_reviews()

    return jsonify({"history": reviews})


if __name__ == "__main__":
    app.run(port=5000, debug=True)
