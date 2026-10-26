import re
import jwt
import datetime
from flask import Blueprint, request, jsonify
from werkzeug.security import generate_password_hash, check_password_hash
from mysql.connector import Error as MySQLError

from database.mysql import fetch_one, execute
from config import Config

auth_bp = Blueprint("auth", __name__, url_prefix="/api/auth")

EMAIL_REGEX = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")


def make_token(user_id, email):
    payload = {
        "user_id": user_id,
        "email": email,
        "exp": datetime.datetime.utcnow() + datetime.timedelta(hours=Config.JWT_EXPIRY_HOURS),
    }
    return jwt.encode(payload, Config.JWT_SECRET, algorithm="HS256")


@auth_bp.route("/register", methods=["POST"])
def register():
    data = request.get_json(silent=True) or {}
    name = (data.get("name") or "").strip()
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not name or not email or not password:
        return jsonify({"message": "Name, email and password are all required."}), 400
    if not EMAIL_REGEX.match(email):
        return jsonify({"message": "Please enter a valid email address."}), 400
    if len(password) < 6:
        return jsonify({"message": "Password must be at least 6 characters."}), 400

    existing = fetch_one("SELECT id FROM users WHERE email = %s", (email,))
    if existing:
        return jsonify({"message": "An account with this email already exists."}), 409

    password_hash = generate_password_hash(password)

    try:
        user_id = execute(
            "INSERT INTO users (name, email, password_hash) VALUES (%s, %s, %s)",
            (name, email, password_hash),
        )
    except MySQLError as e:
        return jsonify({"message": f"Database error: {str(e)}"}), 500

    token = make_token(user_id, email)
    return jsonify({
        "token": token,
        "user": {"id": user_id, "name": name, "email": email},
    }), 201


@auth_bp.route("/login", methods=["POST"])
def login():
    data = request.get_json(silent=True) or {}
    email = (data.get("email") or "").strip().lower()
    password = data.get("password") or ""

    if not email or not password:
        return jsonify({"message": "Email and password are required."}), 400

    user = fetch_one(
        "SELECT id, name, email, password_hash FROM users WHERE email = %s", (email,)
    )
    if not user or not check_password_hash(user["password_hash"], password):
        return jsonify({"message": "Invalid email or password."}), 401

    token = make_token(user["id"], user["email"])
    return jsonify({
        "token": token,
        "user": {"id": user["id"], "name": user["name"], "email": user["email"]},
    })