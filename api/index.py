from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

# ------------------ App Setup ------------------
app = Flask(__name__)
CORS(app)

# ------------------ MongoDB Connection ------------------
# MongoDB Connection using environment variable
MONGO_URI = os.getenv("MONGO_URI", "mongodb+srv://savan:Kumar123@datasav.n8wcv70.mongodb.net/?retryWrites=true&w=majority&appName=datasav")

try:
    client = MongoClient(MONGO_URI)
    # Test connection
    client.admin.command('ping')
    db = client["datasav"]
    collection = db["tests"]
except Exception as e:
    print(f"MongoDB connection error: {e}")
    client = None
    db = None
    collection = None

# ------------------ Helpers ------------------
def serialize(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def check_db_connection():
    """Check if database connection is available"""
    if not client or not collection:
        return False
    try:
        client.admin.command('ping')
        return True
    except:
        return False

# ------------------ Health Check ------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "API running with MongoDB"})

# ------------------ GET ALL ------------------
@app.route("/api/tests", methods=["GET"])
def get_all_tests():
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    query = {}

    if name := request.args.get("name"):
        query["name"] = {"$regex": name, "$options": "i"}
    if test_type := request.args.get("type"):
        query["type"] = {"$regex": test_type, "$options": "i"}

    try:
        tests = [serialize(t) for t in collection.find(query)]
        return jsonify(tests)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ GET ONE ------------------
@app.route("/api/tests/<string:test_id>", methods=["GET"])
def get_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    try:
        test = collection.find_one({"_id": ObjectId(test_id)})
        if not test:
            return jsonify({"error": "Test not found"}), 404

        return jsonify(serialize(test))
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ CREATE ------------------
@app.route("/api/tests", methods=["POST"])
def add_tests():
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 415

    payload = request.get_json()

    try:
        if isinstance(payload, list):
            result = collection.insert_many(payload)
            ids = [str(i) for i in result.inserted_ids]
        elif isinstance(payload, dict):
            result = collection.insert_one(payload)
            ids = [str(result.inserted_id)]
        else:
            return jsonify({"error": "Invalid payload format"}), 400

        return jsonify({"inserted": len(ids), "ids": ids}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ UPDATE ------------------
@app.route("/api/tests/<string:test_id>", methods=["PUT"])
def update_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 415

    updated_fields = request.get_json()
    if not updated_fields:
        return jsonify({"error": "No data provided"}), 400

    try:
        result = collection.update_one(
            {"_id": ObjectId(test_id)},
            {"$set": updated_fields}
        )

        if not result.matched_count:
            return jsonify({"error": "Test not found"}), 404

        return jsonify({"message": "Updated successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ DELETE ------------------
@app.route("/api/tests/<string:test_id>", methods=["DELETE"])
def delete_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    try:
        result = collection.delete_one({"_id": ObjectId(test_id)})

        if not result.deleted_count:
            return jsonify({"error": "Test not found"}), 404

        return jsonify({"message": "Deleted successfully"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ Export for Vercel ------------------
# Export the app for Vercel serverless functions
handler = app
