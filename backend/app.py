from flask import Flask, request, jsonify
from flask_cors import CORS
from extraction import extract_text
from compliance import check_tender_rules

try:
    import database
except:
    database = None

app = Flask(__name__)
CORS(app)

@app.route("/", methods=["GET"])
def home():
    return jsonify({"message": "Server is running!"})

@app.route("/verify", methods=["POST"])
def verify():
    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
        
    file = request.files["file"]
    text = extract_text(file)
    result = check_tender_rules(text)
    
    if database and hasattr(database, "save_result"):
        database.save_result(file.filename, result["status"], result["score"])
        
    return jsonify({
        "filename": file.filename,
        "status": result["status"],
        "score": result["score"]
    })

if __name__ == "__main__":
    app.run(port=5000)