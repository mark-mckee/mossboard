import os
from apiflask import APIFlask
from flask_cors import CORS
from dotenv import load_dotenv

load_dotenv()

from app.config import config_map
from app.extensions import init_db, init_celery


def create_app(config_name=None):
    if config_name is None:
        config_name = os.environ.get("FLASK_ENV", "development")

    app = APIFlask(__name__, title="MOSSBoard API", version="1.0.0")
    app.config.from_object(config_map.get(config_name, config_map["development"]))

    # Send session cookies with every Swagger UI request (needed for admin endpoints)
    app.config["SWAGGER_UI_CONFIG"] = {"withCredentials": True}

    # Extensions
    init_db(app)
    init_celery(app)

    # CORS only for public endpoints
    CORS(app, resources={r"/api/v1/status*":   {"origins": "*"},
                         r"/api/v1/services*": {"origins": "*"},
                         r"/api/v1/metrics*":  {"origins": "*"}})

    # Register blueprints
    from app.api import public_bp, admin_bp, token_bp, monitors_bp, settings_bp, metrics_bp, notifications_bp
    app.register_blueprint(public_bp)
    app.register_blueprint(admin_bp)
    app.register_blueprint(token_bp)
    app.register_blueprint(monitors_bp)
    app.register_blueprint(settings_bp)
    app.register_blueprint(metrics_bp)
    app.register_blueprint(notifications_bp)

    # Add Bearer token security scheme to OpenAPI spec
    @app.spec_processor
    def add_security_schemes(spec):
        spec.setdefault("components", {})
        spec["components"].setdefault("securitySchemes", {})
        spec["components"]["securitySchemes"]["BearerAuth"] = {
            "type": "http",
            "scheme": "bearer",
            "bearerFormat": "API Token",
            "description": "API token generated in Admin → API Tokens.",
        }
        spec["components"]["securitySchemes"]["SessionAuth"] = {
            "type": "apiKey",
            "in": "cookie",
            "name": "session",
            "description": "Log in via /admin first, then come back and use 'Try it out'.",
        }
        # Apply SessionAuth to all /api/v1/admin/* paths
        for path, methods in spec.get("paths", {}).items():
            if "/admin/" in path or path.endswith("/admin"):
                for method_obj in methods.values():
                    if isinstance(method_obj, dict):
                        method_obj.setdefault("security", [{"SessionAuth": []}])

        # Force relative server URL so Swagger UI uses the nginx proxy origin
        spec["servers"] = [{"url": "/"}]
        return spec

    return app
