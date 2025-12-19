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

# Initialize as None - will connect on first request (lazy connection for serverless)
client = None
db = None
collection = None

def get_db_connection():
    """Get or create MongoDB connection (lazy initialization for serverless)"""
    global client, db, collection
    if client is None:
        try:
            print(f"Attempting MongoDB connection...")
            # Increased timeout for better reliability
            client = MongoClient(
                MONGO_URI, 
                serverSelectionTimeoutMS=10000,  # 10 seconds
                connectTimeoutMS=10000,
                socketTimeoutMS=30000,
                retryWrites=True,
                retryReads=True
            )
            db = client["datasav"]
            collection = db["tests"]
            # Quick connection test
            print("Testing MongoDB connection...")
            client.admin.command('ping')
            print("MongoDB connection successful!")
        except Exception as e:
            error_msg = f"MongoDB connection error: {type(e).__name__}: {str(e)}"
            print(error_msg)
            # Reset on error
            try:
                if client:
                    client.close()
            except:
                pass
            client = None
            db = None
            collection = None
    return client, db, collection

# ------------------ Helpers ------------------
def serialize(doc):
    if doc and "_id" in doc:
        doc["_id"] = str(doc["_id"])
    return doc

def check_db_connection():
    """Check if database connection is available"""
    global client, db, collection
    try:
        get_db_connection()  # This updates the global variables
        if not client or not collection:
            print("MongoDB client or collection is None")
            return False
        # Test connection with ping
        client.admin.command('ping')
        return True
    except Exception as e:
        print(f"DB connection check failed: {type(e).__name__}: {e}")
        # Reset connection on failure
        try:
            if client:
                client.close()
        except:
            pass
        client = None
        db = None
        collection = None
        return False

# ------------------ Health Check ------------------
@app.route("/", methods=["GET"])
def index():
    try:
        db_status = check_db_connection()
        response = {
            "status": "ok", 
            "message": "API running with MongoDB",
            "mongo_uri_set": bool(MONGO_URI),
            "db_connected": db_status
        }
        if not db_status:
            response["error"] = "MongoDB connection failed. Check network settings and connection string."
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "mongo_uri_set": bool(MONGO_URI),
            "db_connected": False,
            "error_type": type(e).__name__
        }), 500

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

# ------------------ Global Error Handler ------------------
from werkzeug.exceptions import HTTPException
import traceback

@app.errorhandler(HTTPException)
def handle_http_exception(e):
    """Handle HTTP exceptions"""
    return jsonify({"error": e.name, "message": str(e.description)}), e.code

@app.errorhandler(Exception)
def handle_general_exception(e):
    """Handle all other unhandled exceptions"""
    print(f"Unhandled exception: {type(e).__name__}: {e}")
    traceback.print_exc()
    return jsonify({"error": "Internal server error", "message": str(e)}), 500

# ------------------ Export for Vercel ------------------
# Vercel Python serverless function handler
# Export the Flask app as 'handler' for Vercel Python runtime
handler = app

# ------------------ Run Locally ------------------
if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5000)
