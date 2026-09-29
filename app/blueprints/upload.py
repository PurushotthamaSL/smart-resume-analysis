import uuid
from pathlib import Path
from flask import Blueprint, request, jsonify, redirect, url_for, flash, current_app
from werkzeug.utils import secure_filename

from app.models import db, Resume, JobRole, JobMatch, Recommendation
from app.nlp import ResumeParser, SkillExtractor, ResumeScorer, JobMatcher, SkillRecommender

upload_bp = Blueprint("upload", __name__, url_prefix="/upload")


def allowed_file(filename: str, allowed_extensions: set) -> bool:
    """Check if file has an allowed extension."""
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def client_wants_json() -> bool:
    """Detect if client expects a JSON response."""
    return (
        request.is_json
        or request.headers.get("X-Requested-With") == "XMLHttpRequest"
        or "application/json" in request.headers.get("Accept", "")
        or request.path.startswith("/api/")
    )


@upload_bp.route("/", methods=["GET", "POST"])
@upload_bp.route("", methods=["GET", "POST"])
def upload_file():
    """
    Handle resume upload (PDF, DOCX, TXT) or raw text submission,
    trigger NLP processing pipeline, save results into database,
    and return analysis JSON or redirect URL.
    """
    if request.method == "GET":
        return redirect(url_for("main.index"))

    wants_json = client_wants_json()
    save_path = None
    original_filename = "resume_submission.txt"
    file_ext = "txt"
    file_size = 0
    raw_text = ""

    # Check for file in request (supporting both 'resume' and 'file' field names)
    file = request.files.get("resume") or request.files.get("file")

    # If no file uploaded, check for direct text payload (JSON or form body)
    if not file or not (file.filename or "").strip():
        payload = request.get_json(silent=True) or {}
        raw_text = (
            payload.get("text")
            or payload.get("resume_text")
            or payload.get("resume")
            or payload.get("content")
            or request.form.get("text")
            or request.form.get("resume_text")
            or request.form.get("resume")
            or ""
        ).strip()

        if not raw_text:
            err_msg = "No resume file or text provided in the request."
            if wants_json:
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "danger")
            return redirect(url_for("main.index"))

        file_size = len(raw_text.encode("utf-8"))
        original_filename = payload.get("filename") or "pasted_resume.txt"
        file_ext = "txt"

    else:
        # File was uploaded
        filename = file.filename or "upload"
        allowed_exts = current_app.config.get("ALLOWED_EXTENSIONS", {"pdf", "docx", "txt"})
        if not allowed_file(filename, allowed_exts):
            err_msg = f"Invalid file type. Supported formats: {', '.join(sorted(allowed_exts)).upper()}."
            if wants_json:
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "danger")
            return redirect(url_for("main.index"))

        original_filename = secure_filename(filename) or "resume_upload"
        file_ext = original_filename.rsplit(".", 1)[1].lower() if "." in original_filename else "docx"
        unique_filename = f"{uuid.uuid4().hex[:10]}_{original_filename}"
        upload_folder = Path(current_app.config["UPLOAD_FOLDER"])
        upload_folder.mkdir(parents=True, exist_ok=True)
        save_path = upload_folder / unique_filename

        try:
            file.save(str(save_path))
            file_size = save_path.stat().st_size
        except Exception as e:
            err_msg = f"Failed to save uploaded file: {str(e)}"
            if wants_json:
                return jsonify({"success": False, "error": err_msg}), 500
            flash(err_msg, "danger")
            return redirect(url_for("main.index"))

    # Execute NLP Processing Pipeline
    try:
        parser = ResumeParser()
        if save_path:
            raw_text = parser.extract_text_from_file(str(save_path))

        if not raw_text or len(raw_text.strip()) < 30:
            if save_path and save_path.exists():
                try:
                    save_path.unlink()
                except Exception:
                    pass
            err_msg = "The resume contains very little or no readable text. Please provide a text-based document or paste resume text."
            if wants_json:
                return jsonify({"success": False, "error": err_msg}), 400
            flash(err_msg, "danger")
            return redirect(url_for("main.index"))

        # Step A: Parsing & Entity Extraction
        parsed_data = parser.parse(raw_text, filename=original_filename)

        # Step B: Skill Extraction
        taxonomy_path = str(current_app.config.get("SKILLS_TAXONOMY_PATH", ""))
        extractor = SkillExtractor(taxonomy_path=taxonomy_path)
        extracted_skills = extractor.extract_skills(raw_text)

        # Step C: Resume & ATS Scoring
        scorer = ResumeScorer()
        scores = scorer.calculate_scores(parsed_data, extracted_skills)

        # Step D: Job Role Matching
        roles = JobRole.query.all()
        roles_data = [r.to_dict() for r in roles] if roles else None

        job_roles_path = str(current_app.config.get("JOB_ROLES_PATH", ""))
        matcher = JobMatcher(job_roles_path=job_roles_path)
        if roles_data:
            matcher.set_job_roles(roles_data)

        job_matches = matcher.match_resume(raw_text, extracted_skills.get("unique_names", []), top_n=5)

        # Step E: Skill Recommendations
        learning_res_path = str(current_app.config.get("LEARNING_RESOURCES_PATH", ""))
        recommender = SkillRecommender(resources_path=learning_res_path)
        recommendations = recommender.recommend(job_matches, limit=6)

        # Step F: Save to Database
        resume_record = Resume(
            filename=original_filename,
            file_type=file_ext,
            file_size=file_size,
            raw_text=raw_text,
            candidate_name=parsed_data.get("name") or "Candidate",
            candidate_email=parsed_data.get("email"),
            candidate_phone=parsed_data.get("phone"),
            completeness_score=scores.get("completeness_score", 0.0),
            ats_score=scores.get("ats_score", 0.0),
        )
        resume_record.education = parsed_data.get("education", [])
        resume_record.experience = parsed_data.get("experience", [])
        resume_record.certifications = parsed_data.get("certifications", [])
        resume_record.skills = extracted_skills.get("skills", [])
        resume_record.ats_feedback = scores

        db.session.add(resume_record)
        db.session.flush()

        # Save matches
        for m in job_matches:
            match_record = JobMatch(
                resume_id=resume_record.id,
                job_role_id=m.get("job_role_id"),
                match_percentage=m.get("match_percentage", 0.0),
                tfidf_score=m.get("tfidf_score", 0.0),
            )
            match_record.matched_skills = m.get("matched_skills", [])
            match_record.missing_skills = m.get("missing_skills", [])
            match_record.matched_preferred_skills = m.get("matched_preferred_skills", [])
            db.session.add(match_record)

        # Save recommendations
        for rec in recommendations:
            rec_record = Recommendation(
                resume_id=resume_record.id,
                skill_name=rec.get("skill_name"),
                target_job_role=rec.get("target_job_role"),
                priority=rec.get("priority", "Medium"),
            )
            rec_record.resources = rec.get("resources", [])
            db.session.add(rec_record)

        db.session.commit()

        analysis_url = url_for("analysis.view_analysis", resume_id=resume_record.id)

        if wants_json:
            return jsonify({
                "success": True,
                "resume_id": resume_record.id,
                "redirect_url": analysis_url,
                "analysis_url": analysis_url,
                "message": "Resume analyzed successfully!",
                "candidate": {
                    "id": resume_record.id,
                    "name": resume_record.candidate_name,
                    "email": resume_record.candidate_email,
                    "phone": resume_record.candidate_phone,
                    "scores": scores,
                    "skills_count": len(resume_record.skills),
                },
                "job_matches": job_matches,
                "recommendations": recommendations,
            })

        return redirect(analysis_url)

    except Exception as e:
        db.session.rollback()
        if save_path and save_path.exists():
            try:
                save_path.unlink()
            except Exception:
                pass

        err_msg = f"Error during resume analysis: {str(e)}"
        if wants_json:
            return jsonify({"success": False, "error": err_msg}), 500

        flash(err_msg, "danger")
        return redirect(url_for("main.index"))
