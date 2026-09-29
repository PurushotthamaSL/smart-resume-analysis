from flask import Blueprint, render_template
from app.models import Resume, JobRole

main_bp = Blueprint("main", __name__)


@main_bp.route("/")
def index():
    """Render landing page with upload widget, recent analyses, and sample resumes."""
    recent_resumes = Resume.query.order_by(Resume.uploaded_at.desc()).limit(12).all()
    roles_count = JobRole.query.count()
    return render_template("index.html", recent_resumes=recent_resumes, roles_count=roles_count)


@main_bp.route("/roles", methods=["GET"])
def roles_alias():
    """Alias for /api/roles returning benchmark job roles."""
    from app.blueprints.api import get_roles
    return get_roles()


@main_bp.route("/analyze", methods=["POST", "OPTIONS"])
def analyze_alias():
    """Alias for /api/analyze."""
    from app.blueprints.api import analyze_text
    return analyze_text()


@main_bp.route("/analyze/<int:resume_id>", methods=["GET"])
def analyze_id_alias(resume_id: int):
    """Alias for /analysis/<id>."""
    from app.blueprints.analysis import view_analysis
    return view_analysis(resume_id)


@main_bp.route("/recommend/<int:resume_id>", methods=["GET"])
def recommend_id_alias(resume_id: int):
    """Alias for /recommendations/<id>."""
    from app.blueprints.recommendation import view_recommendations
    return view_recommendations(resume_id)
