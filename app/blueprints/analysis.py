import json
from pathlib import Path
from flask import Blueprint, render_template, jsonify, request, Response, redirect, url_for, flash, current_app
from app.models import db, Resume, JobMatch, Recommendation

from app.utils.pdf_generator import generate_resume_pdf
from app.utils.rating import compute_star_rating

analysis_bp = Blueprint("analysis", __name__, url_prefix="/analysis")


@analysis_bp.route("/<int:resume_id>", methods=["GET"])
def view_analysis(resume_id: int):
    """Render the rich interactive analysis dashboard for a parsed resume, or return JSON."""
    resume = db.get_or_404(Resume, resume_id)

    if request.is_json or "application/json" in request.headers.get("Accept", ""):
        return jsonify(resume.to_dict())

    matches = JobMatch.query.filter_by(resume_id=resume.id).order_by(JobMatch.match_percentage.desc()).all()
    recommendations = Recommendation.query.filter_by(resume_id=resume.id).all()

    # Group extracted skills by category for organized display
    skills_by_category = {}
    for skill_item in resume.skills:
        cat = skill_item.get("category", "General")
        if cat not in skills_by_category:
            skills_by_category[cat] = []
        skills_by_category[cat].append(skill_item.get("name"))

    matches_data = [m.to_dict() for m in matches]
    recommendations_data = [r.to_dict() for r in recommendations]

    # Compute 5-star rating values for template rendering (no math in Jinja)
    star_rating, full_stars, half_star, empty_stars = compute_star_rating(resume.ats_score)

    return render_template(
        "analysis.html",
        resume=resume,
        matches=matches,
        matches_data=matches_data,
        recommendations=recommendations,
        recommendations_data=recommendations_data,
        skills_by_category=skills_by_category,
        ats_feedback=resume.ats_feedback,
        star_rating=star_rating,
        full_stars=full_stars,
        half_star=half_star,
        empty_stars=empty_stars,
    )


@analysis_bp.route("/<int:resume_id>/json", methods=["GET"])
def get_analysis_json(resume_id: int):
    """Return complete analysis details in JSON format."""
    resume = db.get_or_404(Resume, resume_id)
    return jsonify(resume.to_dict())


@analysis_bp.route("/<int:resume_id>/export", methods=["GET"])
@analysis_bp.route("/<int:resume_id>/export-pdf", methods=["GET"])
def export_analysis(resume_id: int):
    """Export formatted analysis report as a downloadable PDF document."""
    resume = db.get_or_404(Resume, resume_id)
    pdf_bytes = generate_resume_pdf(resume)
    safe_name = "".join(c for c in (resume.candidate_name or "candidate") if c.isalnum() or c in ("-", "_")).strip() or "candidate"
    filename = f"resume_analysis_{resume.id}_{safe_name}.pdf"
    return Response(
        pdf_bytes,
        mimetype="application/pdf",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'}
    )


@analysis_bp.route("/<int:resume_id>/export_pdf", methods=["GET"])
def export_pdf(resume_id: int):
    """Alias for export_analysis to support explicit PDF endpoint naming."""
    return export_analysis(resume_id)


@analysis_bp.route("/delete/<int:resume_id>", methods=["GET", "POST", "DELETE"])
@analysis_bp.route("/<int:resume_id>/delete", methods=["GET", "POST", "DELETE"])
def delete_resume(resume_id: int):
    """Delete an analyzed resume and its cascaded job matches and recommendations."""
    resume = db.get_or_404(Resume, resume_id)
    candidate_label = resume.candidate_name or resume.filename or f"ID #{resume_id}"

    # Clean up uploaded file on disk if one exists
    upload_folder = current_app.config.get("UPLOAD_FOLDER")
    if upload_folder and resume.filename:
        try:
            folder_path = Path(upload_folder)
            for f in folder_path.glob(f"*_{resume.filename}"):
                if f.is_file():
                    f.unlink()
        except Exception:
            pass

    db.session.delete(resume)
    db.session.commit()

    is_json = (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
    )
    if is_json:
        return jsonify({
            "success": True,
            "message": f"Resume analysis for '{candidate_label}' has been successfully deleted.",
            "deleted_id": resume_id
        }), 200

    flash(f"Resume analysis for '{candidate_label}' was successfully deleted.", "success")
    return redirect(url_for("main.index"))


# Alias for route convenience
delete_analysis = delete_resume


