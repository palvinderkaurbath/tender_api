from flask import Flask, request, jsonify
import pymysql
import os
from datetime import datetime
from flask_cors import CORS



app = Flask(__name__)
CORS(app)

DB_CONFIG = {
    'host': os.environ.get('DB_HOST', '154.61.74.229'),
    'user': os.environ.get('DB_USER', 'remote_user2'),
    'password': os.environ.get('DB_PASSWORD', 'Cadabraa2024'),
    'database': os.environ.get('DB_NAME', 'tenderalert'),
    'cursorclass': __import__('pymysql').cursors.DictCursor,
}

def get_db_connection():
    return pymysql.connect(**DB_CONFIG)

@app.route("/db-check")
def db_check():
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("SELECT 1")
        result = cursor.fetchone()
        cursor.close()
        conn.close()
        return f"DB Connected! Result: {result}", 200
    except Exception as e:
        return f"DB Connection Error: {e}", 500

@app.route("/", methods=["GET"])
def health_check():
    return "API is alive", 200

# --- Register or Insert Client ---
@app.route("/register-client", methods=["POST"])
def register_client():
    from flask import request, jsonify
    import pymysql

    data = request.get_json()
    client_id = data.get("client_id")
    keywords = data.get("keywords", [])
    states = data.get("states", [])

    if not client_id or not keywords:
        return jsonify({"error": "client_id and keywords are required"}), 400

    keywords_str = ",".join(keywords)
    states_str = ",".join(states)

    conn = None
    cursor = None

    try:
        conn = pymysql.connect(**DB_CONFIG)
        cursor = conn.cursor()

        # Check if client_id already exists
        cursor.execute("SELECT 1 FROM client_keywords WHERE client_id = %s", (client_id,))
        if cursor.fetchone():
            return jsonify({"message": "Client ID already exists. Please use the update endpoint to modify keywords or states."}), 200

        # Insert new client
        cursor.execute("""
            INSERT INTO client_keywords (client_id, keywords, states)
            VALUES (%s, %s, %s)
        """, (client_id, keywords_str, states_str))
        conn.commit()

        return jsonify({"message": "Client registered successfully."}), 201

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor:
            cursor.close()
        if conn:
            conn.close()


# --- Update Existing Client ---
@app.route("/update-client", methods=["POST"])
def update_client():
    data = request.get_json()
    print("🔧 Received update request:", data)

    client_id = data.get("client_id")
    keywords = data.get("keywords")
    states = data.get("states")

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    conn = None
    cursor = None

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        updates = []
        values = []

        if keywords is not None:
            updates.append("keywords = %s")
            values.append(",".join(keywords))

        if states is not None:
            updates.append("states = %s")
            values.append(",".join(states))

        if not updates:
            return jsonify({"error": "No fields to update"}), 400

        updates.append("modified_at = CURRENT_TIMESTAMP")
        values.append(client_id)

        query = f"UPDATE client_keywords SET {', '.join(updates)} WHERE client_id = %s"
        print("📝 Executing query:", query)
        cursor.execute(query, tuple(values))
        conn.commit()

        return jsonify({"message": "Client updated successfully."})

    except Exception as e:
        print("❌ Update client error:", str(e))
        return jsonify({"error": str(e)}), 500

    finally:
        if cursor: cursor.close()
        if conn: conn.close()


# --- Get Client Info ---
@app.route("/get-client", methods=["POST"])
def get_client():
    data = request.get_json()
    client_id = data.get("client_id")

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT client_id, keywords, states, added_at, modified_at
            FROM client_keywords
            WHERE client_id = %s
        """, (client_id,))
        row = cursor.fetchone()
        if not row:
            return jsonify({"error": "Client not found"}), 404

        row["keywords"] = row["keywords"].split(",") if row["keywords"] else []
        row["states"] = row["states"].split(",") if row["states"] else []
        return jsonify(row)
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

# --- Get Client Tender Matches ---
@app.route("/client-matches", methods=["POST"])
def get_client_matches():
    data = request.get_json()
    client_id = data.get("client_id")

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute("""
            SELECT g.id, g.bid_number, g.item, g.quantity, g.start_date, g.end_date,
                   g.department, g.location_state, t.score, t.matched_at
            FROM tender_match_results t
            JOIN gem_bids g ON t.tender_id = g.id
            WHERE t.client_id = %s
            ORDER BY t.matched_at DESC
        """, (client_id,))
        rows = cursor.fetchall()
        return jsonify({"matches": rows})
    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()



@app.route("/client-master-tenders", methods=["POST"])
def get_master_tenders_for_client():
    data = request.get_json()
    client_id = data.get("client_id")

    if not client_id:
        return jsonify({"error": "client_id is required"}), 400

    try:
        conn = get_db_connection()
        cursor = conn.cursor()

        # Only select relevant columns and exclude 'id'
        cursor.execute("""
            SELECT 
                m.tgo_id, m.bid_id, m.bid_item_desc, m.bid_link, m.bid_qty,
                m.bid_end_date, m.dept, m.location_city, m.location_pincode,
                m.location_state, m.source_id, mtm.score, mtm.matched_keyword
            FROM master_table m
            JOIN master_tender_match mtm ON m.id = mtm.tender_id
            WHERE mtm.client_id = %s
              AND m.bid_end_date > NOW()
            ORDER BY m.bid_end_date ASC
        """, (client_id,))

        rows = cursor.fetchall()
        return jsonify({"tenders": rows})

    except Exception as e:
        return jsonify({"error": str(e)}), 500

    finally:
        cursor.close()
        conn.close()


@app.route("/general-search", methods=["POST", "OPTIONS"])
def general_search():
    if request.method == "OPTIONS":
        # 🔁 This is a preflight request, just approve it
        return '', 200

    # ✅ Now handle actual POST
    data = request.get_json()
    if not data or "keywords" not in data:
        return jsonify({"error": "'keywords' field is required"}), 400


    keyword_phrases = data.get("keywords", [])
    state = data.get("state")  # optional

    # ✅ Validate input
    if not keyword_phrases or len(keyword_phrases) != 1:
        return jsonify({"error": "'keywords' must contain exactly one phrase"}), 400

    phrase = keyword_phrases[0].strip().lower()

    # ✅ Stopwords to exclude
    STOPWORDS = {
        "the", "a", "an", "of", "for", "in", "to", "and", "with",
        "on", "by", "at", "from", "is", "this", "that", "as", "be", "are", "it"
    }

    # ✅ Split and filter stopwords
    search_words = [word for word in phrase.split() if word not in STOPWORDS]

    if not search_words:
        return jsonify({"error": "No valid searchable words after removing stopwords"}), 400

    # ✅ Prepare SQL LIKE conditions
    like_clauses = " OR ".join(["LOWER(bid_item_desc) LIKE %s" for _ in search_words])
    values = [f"%{word}%" for word in search_words]

    # ✅ SQL query
    query = f"""
        SELECT *
        FROM tenderalert.master_table
        WHERE ({like_clauses})
          AND bid_end_date > NOW()
    """
    if state:
        query += " AND LOWER(location_state) = %s"
        values.append(state.lower())

    query += " LIMIT 500"

    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(query, values)
        rows = cursor.fetchall()

        # ✅ Calculate match percentage
        enriched = []
        for row in rows:
            desc = row.get("bid_item_desc", "").lower()
            matched = sum(1 for word in search_words if word in desc)
            percent = round((matched / len(search_words)) * 100, 2)
            row["match_percent"] = percent
            enriched.append(row)

        # ✅ Sort by match %
        enriched.sort(key=lambda x: x["match_percent"], reverse=True)

        return jsonify({"results": enriched})

    except Exception as e:
        return jsonify({"error": str(e)}), 500
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    PORT = int(os.environ.get("PORT", 5000))
    app.run(
        host="0.0.0.0",
        port=PORT,
        # ssl_context=("ssl/cert.pem", "ssl/key.pem"),
        debug=True
    )

