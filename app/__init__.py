import os
from pathlib import Path

from flask import Flask, jsonify, render_template, request

from .db import init_app
from .routes import bp


def create_app(test_config=None):
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY=os.getenv("SECRET_KEY", "celebrio-local-development-key"),
        DATABASE=os.getenv("DATABASE_PATH", str(Path(app.instance_path) / "celebrio.sqlite3")),
        MAX_CONTENT_LENGTH=1024 * 1024,
    )
    if test_config:
        app.config.update(test_config)
    Path(app.instance_path).mkdir(parents=True, exist_ok=True)
    init_app(app)
    app.register_blueprint(bp)

    @app.errorhandler(404)
    def not_found(error):
        if request.is_json or request.path.startswith("/api/"):
            return jsonify(error="Not found"), 404
        return render_template("404.html"), 404

    @app.errorhandler(413)
    def too_large(error):
        return jsonify(error="Request is too large"), 413

    return app
