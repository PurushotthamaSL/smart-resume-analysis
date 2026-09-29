import json
from pathlib import Path
from flask import Flask

from config import config_by_name
from app.models import db, JobRole


def create_app(config_name: str = "default") -> Flask:
    """Flask application factory."""
    app = Flask(
        __name__,
        template_folder=str(Path(__file__).resolve().parent.parent / "templates"),
        static_folder=str(Path(__file__).resolve().parent.parent / "static"),
    )

    # Load configuration
    cfg_class = config_by_name.get(config_name, config_by_name["default"])
    app.config.from_object(cfg_class)

    # Ensure required directories exist
    upload_dir = Path(app.config["UPLOAD_FOLDER"])
    upload_dir.mkdir(parents=True, exist_ok=True)

    instance_dir = Path(app.instance_path)
    instance_dir.mkdir(parents=True, exist_ok=True)

    # Initialize extensions
    db.init_app(app)

    # Initialize CORS for cross-origin frontend support
    try:
        from flask_cors import CORS
        cors_origins = app.config.get("CORS_ORIGINS", "*")
        if isinstance(cors_origins, str):
            if cors_origins.strip() == "*":
                origins_val = "*"
            else:
                origins_val = [o.strip() for o in cors_origins.split(",") if o.strip()]
        else:
            origins_val = cors_origins

        CORS(
            app,
            resources={r"/*": {"origins": origins_val}},
            supports_credentials=True,
            allow_headers=["Content-Type", "Authorization", "X-Requested-With", "Accept"],
            methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
        )
    except ImportError:
        pass

    # Register Blueprints
    from app.blueprints.main import main_bp
    from app.blueprints.upload import upload_bp
    from app.blueprints.analysis import analysis_bp
    from app.blueprints.recommendation import recommendation_bp
    from app.blueprints.api import api_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(upload_bp)
    app.register_blueprint(analysis_bp)
    app.register_blueprint(recommendation_bp)
    app.register_blueprint(api_bp)

    # Register JSON-aware error handlers
    @app.errorhandler(404)
    def not_found(e):
        from flask import request, jsonify, render_template
        if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
            return jsonify({"success": False, "error": "Resource not found", "status_code": 404}), 404
        return render_template("base.html"), 404

    @app.errorhandler(500)
    def internal_error(e):
        from flask import request, jsonify
        db.session.rollback()
        if request.is_json or request.path.startswith("/api/") or "application/json" in request.headers.get("Accept", ""):
            return jsonify({"success": False, "error": "Internal server error", "status_code": 500}), 500
        return "Internal Server Error", 500

    # Initialize database tables and seed default roles
    with app.app_context():
        db.create_all()
        _seed_job_roles_if_empty(app)


    # Custom Jinja filters
    @app.template_filter("score_color")
    def score_color_filter(score):
        try:
            val = float(score)
            if val >= 80:
                return "emerald"
            elif val >= 60:
                return "indigo"
            elif val >= 40:
                return "amber"
            else:
                return "rose"
        except (ValueError, TypeError):
            return "slate"

    return app


def _seed_job_roles_if_empty(app: Flask):
    """Seed benchmark job roles into SQLite if the table is currently empty."""
    try:
        if JobRole.query.count() == 0:
            roles_file = Path(app.config["JOB_ROLES_PATH"])
            if roles_file.exists():
                with open(roles_file, "r", encoding="utf-8") as f:
                    roles_data = json.load(f)

                for item in roles_data:
                    role = JobRole(
                        id=item.get("id"),
                        title=item.get("title"),
                        domain=item.get("domain"),
                        experience_level=item.get("experience_level", "Mid-Level"),
                        description=item.get("description", ""),
                    )
                    role.required_skills = item.get("required_skills", [])
                    role.preferred_skills = item.get("preferred_skills", [])
                    role.keywords = item.get("keywords", [])
                    db.session.add(role)

                db.session.commit()
    except Exception as e:
        db.session.rollback()
        print(f"[create_app] Notice: Database seeding skipped or error: {e}")
