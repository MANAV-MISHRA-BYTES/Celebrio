import os
import secrets
import threading
import time
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .db import init_app
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY") or secrets.token_hex(32),
        DATABASE=os.getenv("DATABASE_PATH", str(Path(app.instance_path) / "celebrio.sqlite3")),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_app(app)
    app.register_blueprint(bp)
    request_times = {}
    request_lock = threading.Lock()
    last_cleanup = [time.monotonic()]

    @app.before_request
    def limit_ai_requests():
        limits = {"main.create_event": 5, "main.ai_action": 12}
        limit = limits.get(request.endpoint)
        if limit is None:
            return None
        now = time.monotonic()
        identity = request.remote_addr or "unknown"
        key = (identity, request.endpoint)
        with request_lock:
            if now - last_cleanup[0] > 60:
                for current_key, timestamps in list(request_times.items()):
                    recent = [stamp for stamp in timestamps if now - stamp < 60]
                    if recent:
                        request_times[current_key] = recent
                    else:
                        request_times.pop(current_key, None)
                last_cleanup[0] = now
            recent = [stamp for stamp in request_times.get(key, []) if now - stamp < 60]
            if len(recent) >= limit:
                return jsonify(error="Too many planner requests. Please wait a minute and try again."), 429
            recent.append(now)
            request_times[key] = recent
        return None

    @app.errorhandler(404)
    def not_found(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify(error="Not found"), 404
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Request is too large"), 413

    return app
