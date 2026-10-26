import logging
import threading
import requests
from flask import Flask, jsonify
from flask_cors import CORS
from config import Config, ensure_folders

from routes.analyze import analyze_bp
from routes.auth import auth_bp
from routes.history import history_bp


def _preload_ollama_model():
    def warm_up():
        try:
            requests.post(
                f"{Config.OLLAMA_HOST}/api/generate",
                json={"model": Config.OLLAMA_MODEL, "prompt": "hi", "stream": False, "keep_alive": "30m"},
                timeout=120,
            )
            print(f"Ollama model '{Config.OLLAMA_MODEL}' pre-loaded.")
        except Exception as e:
            print(f"Ollama warm-up failed (will load on first real request instead): {e}")

    threading.Thread(target=warm_up, daemon=True).start()


def create_app():
    ensure_folders()

    app = Flask(__name__)
    app.config.from_object(Config)

    CORS(
        app,
        resources={r"/api/*": {"origins": "*"}},
        supports_credentials=False,
    )

    logging.basicConfig(
        level=logging.DEBUG if Config.DEBUG else logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    app.register_blueprint(analyze_bp)
    app.register_blueprint(auth_bp)
    app.register_blueprint(history_bp)

    @app.route("/api/health", methods=["GET"])
    def health():
        return jsonify({"status": "ok", "service": "AI Code Analysis & Optimizer"})

    @app.errorhandler(404)
    def not_found(e):
        return jsonify({"error": "Endpoint not found"}), 404

    @app.errorhandler(500)
    def server_error(e):
        app.logger.exception("Internal server error")
        return jsonify({"error": "Internal server error"}), 500


    _preload_ollama_model()

    return app


if __name__ == "__main__":
    app = create_app()
    app.run(host="0.0.0.0", port=5000, debug=Config.DEBUG)