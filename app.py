from flask import Flask, request, jsonify
from flask_cors import CORS
import sqlite3
import re
import os
from datetime import datetime
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
CORS(app, origins=os.getenv("ALLOWED_ORIGIN", "*"))

DB_NAME = "subscribers.db"

# ── DB SETUP ──────────────────────────────────────────────
def init_db():
    conn = sqlite3.connect(DB_NAME)
    conn.execute("""
        CREATE TABLE IF NOT EXISTS subscribers (
            id        INTEGER PRIMARY KEY AUTOINCREMENT,
            email     TEXT UNIQUE NOT NULL,
            name      TEXT,
            source    TEXT DEFAULT 'tranquil-labs',
            signed_up TEXT DEFAULT (datetime('now'))
        )
    """)
    conn.commit()
    conn.close()

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

# ── HELPERS ───────────────────────────────────────────────
def is_valid_email(email):
    return re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", email)

# ── ROUTES ────────────────────────────────────────────────

@app.route("/", methods=["GET"])
def health():
    return jsonify({"status": "ok", "message": "Tranquil Labs backend is running 🌿"})


SUBSTACK_URL = "https://littlehugs.substack.com/?utm_campaign=profile&utm_medium=profile-page"

@app.route("/subscribe", methods=["POST"])
def subscribe():
    data = request.get_json()

    email = (data.get("email") or "").strip().lower()
    name  = (data.get("name") or "").strip()

    if not email:
        return jsonify({"error": "Email is required."}), 400

    if not is_valid_email(email):
        return jsonify({"error": "That doesn't look like a valid email."}), 400

    try:
        conn = get_db()
        conn.execute(
            "INSERT INTO subscribers (email, name) VALUES (?, ?)",
            (email, name or None)
        )
        conn.commit()
        conn.close()
        return jsonify({
            "message": "Almost there! We're opening Substack so you can confirm your subscription 💌",
            "redirect": SUBSTACK_URL,
            "already_subscribed": False
        }), 201

    except sqlite3.IntegrityError:
        return jsonify({
            "message": "You're already on our list 🌿 Opening Substack just in case!",
            "redirect": SUBSTACK_URL,
            "already_subscribed": True
        }), 200


@app.route("/subscribers", methods=["GET"])
def list_subscribers():
    secret = request.headers.get("X-Admin-Key")
    if secret != os.getenv("ADMIN_KEY", "changeme"):
        return jsonify({"error": "Not authorised."}), 401

    conn = get_db()
    rows = conn.execute(
        "SELECT id, email, name, source, signed_up FROM subscribers ORDER BY signed_up DESC"
    ).fetchall()
    conn.close()

    return jsonify([dict(row) for row in rows]), 200


@app.route("/subscribers/<int:sub_id>", methods=["DELETE"])
def delete_subscriber(sub_id):
    secret = request.headers.get("X-Admin-Key")
    if secret != os.getenv("ADMIN_KEY", "changeme"):
        return jsonify({"error": "Not authorised."}), 401

    conn = get_db()
    conn.execute("DELETE FROM subscribers WHERE id = ?", (sub_id,))
    conn.commit()
    conn.close()
    return jsonify({"message": "Subscriber removed."}), 200


# ── START ──────────────────────────────────────────────────
if __name__ == "__main__":
    init_db()
    app.run(debug=True, port=5000)
