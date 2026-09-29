from flask import Blueprint, render_template, jsonify, request
from app.models import db, Resume, Recommendation

recommendation_bp = Blueprint("recommendation", __name__, url_prefix="/recommendations")


@recommendation_bp.route("/<int:resume_id>", methods=["GET"])
def view_recommendations(resume_id: int):
    """View dedicated learning pathways and skill recommendations for a candidate."""
    resume = db.get_or_404(Resume, resume_id)
    recommendations = Recommendation.query.filter_by(resume_id=resume.id).all()

    if request.is_json or "application/json" in request.headers.get("Accept", ""):
        return jsonify([rec.to_dict() for rec in recommendations])

    return render_template("recommendations.html", resume=resume, recommendations=recommendations)


@recommendation_bp.route("/<int:resume_id>/api", methods=["GET"])
@recommendation_bp.route("/<int:resume_id>/json", methods=["GET"])
def api_recommendations(resume_id: int):
    """JSON API for candidate skill recommendations."""
    recommendations = Recommendation.query.filter_by(resume_id=resume_id).all()
    return jsonify([rec.to_dict() for rec in recommendations])
