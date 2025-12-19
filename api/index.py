from flask import Flask, request, jsonify
from flask_cors import CORS
from pymongo import MongoClient
from bson.objectid import ObjectId
import os

# ------------------ App Setup ------------------
app = Flask(__name__)
CORS(app)

# ------------------ MongoDB Connection ------------------
# ⚠️ MongoDB Connection (Hardcoded – Not recommended for public repos)
MONGO_URI = "mongodb+srv://savan:Kumar123@datasav.n8wcv70.mongodb.net/?retryWrites=true&w=majority&appName=datasav"

client = MongoClient(MONGO_URI)
db = client["datasav"]
collection = db["tests"]

# ------------------ Helpers ------------------
def serialize(doc):
    doc["_id"] = str(doc["_id"])
    return doc

# ------------------ Health Check ------------------
@app.route("/", methods=["GET"])
def index():
    return jsonify({"status": "ok", "message": "API running with MongoDB"})

# ------------------ GET ALL ------------------
@app.route("/api/tests", methods=["GET"])
def get_all_tests():
    query = {}

    if name := request.args.get("name"):
        query["name"] = {"$regex": name, "$options": "i"}
    if test_type := request.args.get("type"):
        query["type"] = {"$regex": test_type, "$options": "i"}

    tests = [serialize(t) for t in collection.find(query)]
    return jsonify(tests)

# ------------------ GET ONE ------------------
@app.route("/api/tests/<string:test_id>", methods=["GET"])
def get_test(test_id):
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    test = collection.find_one({"_id": ObjectId(test_id)})
    if not test:
        return jsonify({"error": "Test not found"}), 404

    return jsonify(serialize(test))

# ------------------ CREATE ------------------
@app.route("/api/tests", methods=["POST"])
def add_tests():
    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 415

    payload = request.get_json()

    if isinstance(payload, list):
        result = collection.insert_many(payload)
        ids = [str(i) for i in result.inserted_ids]
    elif isinstance(payload, dict):
        result = collection.insert_one(payload)
        ids = [str(result.inserted_id)]
    else:
        return jsonify({"error": "Invalid payload format"}), 400

    return jsonify({"inserted": len(ids), "ids": ids}), 201

# ------------------ UPDATE ------------------
@app.route("/api/tests/<string:test_id>", methods=["PUT"])
def update_test(test_id):
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 415

    updated_fields = request.get_json()
    if not updated_fields:
        return jsonify({"error": "No data provided"}), 400

    result = collection.update_one(
        {"_id": ObjectId(test_id)},
        {"$set": updated_fields}
    )

    if not result.matched_count:
        return jsonify({"error": "Test not found"}), 404

    return jsonify({"message": "Updated successfully"})

# ------------------ DELETE ------------------
@app.route("/api/tests/<string:test_id>", methods=["DELETE"])
def delete_test(test_id):
    if not ObjectId.is_valid(test_id):
        return jsonify({"error": "Invalid ID"}), 400

    result = collection.delete_one({"_id": ObjectId(test_id)})

    if not result.deleted_count:
        return jsonify({"error": "Test not found"}), 404

    return jsonify({"message": "Deleted successfully"})

# ------------------ Export for Vercel ------------------
app
