import jwt
from functools import wraps
from flask import request, jsonify
from config import Config


def get_user_from_token():
    """Extracts and verifies the JWT from the Authorization header.
    Returns the decoded payload dict, or None if missing/invalid."""
    auth_header = request.headers.get("Authorization", "")
    if not auth_header.startswith("Bearer "):
        return None

    token = auth_header.split(" ", 1)[1]
    try:
        payload = jwt.decode(token, Config.JWT_SECRET, algorithms=["HS256"])
        return payload  # {"user_id": ..., "email": ..., "exp": ...}
    except jwt.ExpiredSignatureError:
        return None
    except jwt.InvalidTokenError:
        return None


def require_auth(f):
    """Decorator for routes that MUST have a valid logged-in user."""
    @wraps(f)
    def wrapper(*args, **kwargs):
        user = get_user_from_token()
        if not user:
            return jsonify({"error": "Authentication required. Please log in."}), 401
        request.current_user = user
        return f(*args, **kwargs)
    return wrapper