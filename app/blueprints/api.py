from flask import Blueprint, jsonify, request, current_app
from app.models import db, JobRole, Resume, Recommendation
from app.nlp import ResumeParser, SkillExtractor, ResumeScorer, JobMatcher, SkillRecommender

api_bp = Blueprint("api", __name__, url_prefix="/api")


@api_bp.route("/health", methods=["GET"])
def health_check():
    """Health check endpoint."""
    return jsonify({
        "status": "healthy",
        "service": "Smart Resume Analyzer API",
        "version": "1.0.0"
    })


@api_bp.route("/roles", methods=["GET"])
def get_roles():
    """Return all target job roles."""
    roles = JobRole.query.all()
    return jsonify([r.to_dict() for r in roles])


@api_bp.route("/analyze", methods=["POST", "OPTIONS"])
@api_bp.route("/analyze-text", methods=["POST", "OPTIONS"])
def analyze_text():
    """
    On-the-fly analysis of resume text or uploaded document without requiring database persistence.
    Accepts:
      - JSON: { "text": "...", "target_role": "..." }
      - Form-data: text="...", or file upload (resume=...)
    """
    if request.method == "OPTIONS":
        return jsonify({"status": "ok"}), 200

    text = ""
    # 1. Try reading JSON
    if request.is_json:
        data = request.get_json(silent=True) or {}
        text = (
            data.get("text")
            or data.get("resume_text")
            or data.get("resume")
            or data.get("content")
            or ""
        ).strip()

    # 2. Try reading form data or files if text still empty
    if not text:
        text = (
            request.form.get("text")
            or request.form.get("resume_text")
            or request.form.get("resume")
            or ""
        ).strip()

    # 3. Check for uploaded file if text still empty
    if not text:
        uploaded_file = request.files.get("resume") or request.files.get("file")
        if uploaded_file and (uploaded_file.filename or "").strip():
            parser = ResumeParser()
            try:
                # Save temporarily to extract text
                import tempfile
                from pathlib import Path
                filename = uploaded_file.filename or ""
                ext = Path(filename).suffix.lower() or ".docx"
                with tempfile.NamedTemporaryFile(suffix=ext, delete=False) as tmp:
                    uploaded_file.save(tmp.name)
                    tmp_path = Path(tmp.name)
                try:
                    text = parser.extract_text_from_file(str(tmp_path))
                finally:
                    if tmp_path.exists():
                        try:
                            tmp_path.unlink()
                        except Exception:
                            pass
            except Exception as e:
                return jsonify({
                    "success": False,
                    "error": f"Failed to extract text from uploaded document: {str(e)}"
                }), 400

    if not text or len(text.strip()) < 30:
        return jsonify({
            "success": False,
            "error": "Please provide sufficient resume text (at least 30 characters)."
        }), 400

    try:
        # Execute NLP pipeline
        parser = ResumeParser()
        parsed = parser.parse(text)

        taxonomy_path = str(current_app.config.get("SKILLS_TAXONOMY_PATH", ""))
        extractor = SkillExtractor(taxonomy_path=taxonomy_path)
        extracted_skills = extractor.extract_skills(text)

        scorer = ResumeScorer()
        scores = scorer.calculate_scores(parsed, extracted_skills)

        job_roles_path = str(current_app.config.get("JOB_ROLES_PATH", ""))
        matcher = JobMatcher(job_roles_path=job_roles_path)
        roles = JobRole.query.all()
        if roles:
            matcher.set_job_roles([r.to_dict() for r in roles])
        job_matches = matcher.match_resume(text, extracted_skills.get("unique_names", []), top_n=5)

        learning_res_path = str(current_app.config.get("LEARNING_RESOURCES_PATH", ""))
        recommender = SkillRecommender(resources_path=learning_res_path)
        recommendations = recommender.recommend(job_matches, limit=6)

        return jsonify({
            "success": True,
            "candidate": {
                "name": parsed.get("name"),
                "email": parsed.get("email"),
                "phone": parsed.get("phone"),
                "links": parsed.get("links"),
                "word_count": parsed.get("word_count"),
                "education": parsed.get("education", []),
                "experience": parsed.get("experience", []),
                "certifications": parsed.get("certifications", []),
            },
            "scores": {
                "completeness_score": scores.get("completeness_score"),
                "ats_score": scores.get("ats_score"),
                "strengths": scores.get("strengths"),
                "warnings": scores.get("warnings"),
                "suggestions": scores.get("suggestions"),
                "details": scores.get("details"),
            },
            "skills": extracted_skills,
            "job_matches": job_matches,
            "recommendations": recommendations,
        }), 200

    except Exception as e:
        return jsonify({
            "success": False,
            "error": f"Error during resume analysis: {str(e)}"
        }), 500


@api_bp.route("/upload", methods=["POST", "OPTIONS"])
def api_upload():
    """API endpoint to upload a resume file and save to DB, returning analysis result."""
    from app.blueprints.upload import upload_file
    return upload_file()


@api_bp.route("/analysis/<int:resume_id>", methods=["GET"])
@api_bp.route("/analyze/<int:resume_id>", methods=["GET"])
def get_analysis_by_id(resume_id: int):
    """Return JSON details of an existing analyzed resume by ID."""
    resume = db.session.get(Resume, resume_id)
    if not resume:
        return jsonify({"success": False, "error": f"Resume ID {resume_id} not found."}), 404
    return jsonify({
        "success": True,
        "resume": resume.to_dict()
    }), 200


@api_bp.route("/recommendations/<int:resume_id>", methods=["GET"])
@api_bp.route("/recommend/<int:resume_id>", methods=["GET"])
def get_recommendations_by_id(resume_id: int):
    """Return JSON list of recommendations for an analyzed resume by ID."""
    resume = db.session.get(Resume, resume_id)

    if not resume:
        return jsonify({"success": False, "error": f"Resume ID {resume_id} not found."}), 404

    recs = Recommendation.query.filter_by(resume_id=resume.id).all()
    return jsonify({
        "success": True,
        "resume_id": resume.id,
        "recommendations": [rec.to_dict() for rec in recs]
    }), 200


@api_bp.route("/resumes/<int:resume_id>", methods=["DELETE", "POST"])
@api_bp.route("/analysis/<int:resume_id>", methods=["DELETE", "POST"])
def delete_resume_by_id(resume_id: int):
    """API endpoint to delete an analyzed resume by ID."""
    resume = db.session.get(Resume, resume_id)
    if not resume:
        return jsonify({"success": False, "error": f"Resume ID {resume_id} not found."}), 404

    candidate_label = resume.candidate_name or resume.filename or f"ID #{resume_id}"
    db.session.delete(resume)
    db.session.commit()

    return jsonify({
        "success": True,
        "message": f"Resume analysis for '{candidate_label}' has been successfully deleted.",
        "deleted_id": resume_id
    }), 200

