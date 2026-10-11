from flask import Flask, request, jsonify
from flask_cors import CORS
from extraction import extract_text_from_pdf
from compliance import check_tender_rules

try:
    import database
except ImportError:
    database = None

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Backend server is running successfully!"})

@app.route("/verify", methods=["POST"])
def verify_document():
    if "file" not in request.files:
        return jsonify({"error": "No file was uploaded"}), 400
        
    file = request.files["file"]
    
    if not file.filename.lower().endswith(".pdf"):
        return jsonify({"error": "Please upload a valid PDF file"}), 400
        
    extracted_text = extract_text_from_pdf(file)
    if not extracted_text:
        return jsonify({"error": "Could not read text from this PDF"}), 400
        
    result = check_tender_rules(extracted_text)
    
    if database and hasattr(database, "save_result"):
        database.save_result(file.filename, result["verdict"], result["score"])
        
    return jsonify({
        "filename": file.filename,
        "status": result["verdict"],
        "score": result["score"],
        "passed": result["passed_items"],
        "missing": result["failed_items"]
    }), 200

@app.route("/records", methods=["GET"])
def get_all_records():
    if database and hasattr(database, "get_records"):
        data = database.get_records()
        return jsonify({"records": data}), 200
    return jsonify({"records": []}), 200

if __name__ == "__main__":
    app.run(debug=True, port=5000)