from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import json
import os
from datetime import datetime

# ------------------ App Setup ------------------
app = Flask(__name__)
CORS(app)

# ------------------ SQLite Database Setup ------------------
# SQLite is a built-in database that comes with Python - no external setup needed!
# For Vercel: Use /tmp directory for writable file system
DB_FILE = os.getenv("DB_FILE", "/tmp/database.db" if os.getenv("VERCEL") else "database.db")

def get_db():
    """Get SQLite database connection"""
    conn = sqlite3.connect(DB_FILE)
    conn.row_factory = sqlite3.Row  # This allows accessing columns by name
    return conn

def init_db():
    """Initialize database and create tables if they don't exist"""
    conn = get_db()
    cursor = conn.cursor()
    
    # Create tests table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tests (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            data TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    conn.commit()
    conn.close()
    print("Database initialized successfully!")

# Initialize database on startup
init_db()

# ------------------ Helpers ------------------
def serialize(row):
    """Convert SQLite row to dictionary"""
    if row is None:
        return None
    data = dict(row)
    # Parse JSON data if it exists
    if 'data' in data and isinstance(data['data'], str):
        try:
            data['data'] = json.loads(data['data'])
        except:
            pass
    return data

def check_db_connection():
    """Check if database connection is available"""
    try:
        conn = get_db()
        conn.execute('SELECT 1')
        conn.close()
        return True
    except Exception as e:
        print(f"DB connection check failed: {type(e).__name__}: {e}")
        return False

# ------------------ Health Check ------------------
@app.route("/", methods=["GET"])
def index():
    try:
        db_status = check_db_connection()
        response = {
            "status": "ok", 
            "message": "API running with SQLite database",
            "database": "SQLite (built-in)",
            "db_file": DB_FILE,
            "db_connected": db_status
        }
        if not db_status:
            response["error"] = "Database connection failed."
        return jsonify(response)
    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e),
            "db_connected": False,
            "error_type": type(e).__name__
        }), 500

# ------------------ GET ALL ------------------
@app.route("/api/tests", methods=["GET"])
def get_all_tests():
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503
    
    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Get filter parameters
        name_filter = request.args.get("name")
        type_filter = request.args.get("type")
        
        # Build query
        query = "SELECT * FROM tests WHERE 1=1"
        params = []
        
        if name_filter:
            query += " AND data LIKE ?"
            params.append(f'%"{name_filter}"%')
        
        if type_filter:
            query += " AND data LIKE ?"
            params.append(f'%"type":"{type_filter}"%')
        
        query += " ORDER BY created_at DESC"
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        conn.close()
        
        tests = [serialize(row) for row in rows]
        return jsonify(tests)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ GET ONE ------------------
@app.route("/api/tests/<int:test_id>", methods=["GET"])
def get_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503

    try:
        conn = get_db()
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM tests WHERE id = ?", (test_id,))
        row = cursor.fetchone()
        conn.close()
        
        if not row:
            return jsonify({"error": "Test not found"}), 404

        return jsonify(serialize(row))
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
    ids = []

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        if isinstance(payload, list):
            # Insert multiple records
            for item in payload:
                data_json = json.dumps(item)
                cursor.execute(
                    "INSERT INTO tests (data, created_at, updated_at) VALUES (?, ?, ?)",
                    (data_json, datetime.now(), datetime.now())
                )
                ids.append(cursor.lastrowid)
        elif isinstance(payload, dict):
            # Insert single record
            data_json = json.dumps(payload)
            cursor.execute(
                "INSERT INTO tests (data, created_at, updated_at) VALUES (?, ?, ?)",
                (data_json, datetime.now(), datetime.now())
            )
            ids.append(cursor.lastrowid)
        else:
            conn.close()
            return jsonify({"error": "Invalid payload format"}), 400

        conn.commit()
        conn.close()
        return jsonify({"inserted": len(ids), "ids": ids}), 201
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ UPDATE ------------------
@app.route("/api/tests/<int:test_id>", methods=["PUT"])
def update_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503

    if not request.is_json:
        return jsonify({"error": "JSON body required"}), 415

    updated_data = request.get_json()
    if not updated_data:
        return jsonify({"error": "No data provided"}), 400

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if record exists
        cursor.execute("SELECT id FROM tests WHERE id = ?", (test_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Test not found"}), 404
        
        # Update record
        data_json = json.dumps(updated_data)
        cursor.execute(
            "UPDATE tests SET data = ?, updated_at = ? WHERE id = ?",
            (data_json, datetime.now(), test_id)
        )
        
        conn.commit()
        conn.close()
        return jsonify({"message": "Updated successfully", "id": test_id})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ------------------ DELETE ------------------
@app.route("/api/tests/<int:test_id>", methods=["DELETE"])
def delete_test(test_id):
    if not check_db_connection():
        return jsonify({"error": "Database connection unavailable"}), 503

    try:
        conn = get_db()
        cursor = conn.cursor()
        
        # Check if record exists
        cursor.execute("SELECT id FROM tests WHERE id = ?", (test_id,))
        if not cursor.fetchone():
            conn.close()
            return jsonify({"error": "Test not found"}), 404
        
        # Delete record
        cursor.execute("DELETE FROM tests WHERE id = ?", (test_id,))
        conn.commit()
        conn.close()
        
        return jsonify({"message": "Deleted successfully", "id": test_id})
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
