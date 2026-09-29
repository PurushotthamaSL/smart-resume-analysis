from datetime import datetime
import json
from . import db


class Resume(db.Model):
    """Stores parsed resumes and extracted metadata."""
    __tablename__ = "resumes"

    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(255), nullable=False)
    file_type = db.Column(db.String(10), nullable=False)  # 'pdf' or 'docx'
    file_size = db.Column(db.Integer, default=0)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Raw extracted text
    raw_text = db.Column(db.Text, nullable=False)
    
    # Candidate details
    candidate_name = db.Column(db.String(150), nullable=True)
    candidate_email = db.Column(db.String(150), nullable=True)
    candidate_phone = db.Column(db.String(50), nullable=True)
    candidate_location = db.Column(db.String(100), nullable=True)
    
    # Parsed structured sections (stored as JSON string)
    education_json = db.Column(db.Text, default="[]")
    experience_json = db.Column(db.Text, default="[]")
    certifications_json = db.Column(db.Text, default="[]")
    
    # Extracted skills (JSON string)
    skills_json = db.Column(db.Text, default="[]")
    
    # Resume Scoring & ATS
    completeness_score = db.Column(db.Float, default=0.0)
    ats_score = db.Column(db.Float, default=0.0)
    ats_feedback_json = db.Column(db.Text, default="{}")
    
    # Relationships
    job_matches = db.relationship("JobMatch", backref="resume", cascade="all, delete-orphan", lazy="joined")
    recommendations = db.relationship("Recommendation", backref="resume", cascade="all, delete-orphan", lazy="joined")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def education(self):
        try:
            return json.loads(self.education_json or "[]")
        except Exception:
            return []

    @education.setter
    def education(self, value):
        self.education_json = json.dumps(value)

    @property
    def experience(self):
        try:
            return json.loads(self.experience_json or "[]")
        except Exception:
            return []

    @experience.setter
    def experience(self, value):
        self.experience_json = json.dumps(value)

    @property
    def certifications(self):
        try:
            return json.loads(self.certifications_json or "[]")
        except Exception:
            return []

    @certifications.setter
    def certifications(self, value):
        self.certifications_json = json.dumps(value)

    @property
    def skills(self):
        try:
            return json.loads(self.skills_json or "[]")
        except Exception:
            return []

    @skills.setter
    def skills(self, value):
        self.skills_json = json.dumps(value)

    @property
    def ats_feedback(self):
        try:
            return json.loads(self.ats_feedback_json or "{}")
        except Exception:
            return {}

    @ats_feedback.setter
    def ats_feedback(self, value):
        self.ats_feedback_json = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "filename": self.filename,
            "file_type": self.file_type,
            "file_size": self.file_size,
            "uploaded_at": self.uploaded_at.isoformat() if self.uploaded_at else None,
            "candidate_name": self.candidate_name,
            "candidate_email": self.candidate_email,
            "candidate_phone": self.candidate_phone,
            "candidate_location": self.candidate_location,
            "education": self.education,
            "experience": self.experience,
            "certifications": self.certifications,
            "skills": self.skills,
            "completeness_score": self.completeness_score,
            "ats_score": self.ats_score,
            "ats_feedback": self.ats_feedback,
            "job_matches": [m.to_dict() for m in self.job_matches],
            "recommendations": [r.to_dict() for r in self.recommendations],
        }


class JobRole(db.Model):
    """Stores benchmark job roles for matching and gap analysis."""
    __tablename__ = "job_roles"

    id = db.Column(db.String(100), primary_key=True)
    title = db.Column(db.String(150), nullable=False)
    domain = db.Column(db.String(100), nullable=False)
    experience_level = db.Column(db.String(50), default="Mid-Level")
    description = db.Column(db.Text, nullable=False)
    
    # Lists stored as JSON
    required_skills_json = db.Column(db.Text, default="[]")
    preferred_skills_json = db.Column(db.Text, default="[]")
    keywords_json = db.Column(db.Text, default="[]")
    created_at = db.Column(db.DateTime, default=datetime.utcnow)

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def required_skills(self):
        try:
            return json.loads(self.required_skills_json or "[]")
        except Exception:
            return []

    @required_skills.setter
    def required_skills(self, value):
        self.required_skills_json = json.dumps(value)

    @property
    def preferred_skills(self):
        try:
            return json.loads(self.preferred_skills_json or "[]")
        except Exception:
            return []

    @preferred_skills.setter
    def preferred_skills(self, value):
        self.preferred_skills_json = json.dumps(value)

    @property
    def keywords(self):
        try:
            return json.loads(self.keywords_json or "[]")
        except Exception:
            return []

    @keywords.setter
    def keywords(self, value):
        self.keywords_json = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "title": self.title,
            "domain": self.domain,
            "experience_level": self.experience_level,
            "description": self.description,
            "required_skills": self.required_skills,
            "preferred_skills": self.preferred_skills,
            "keywords": self.keywords,
        }


class JobMatch(db.Model):
    """Stores match results and skill gaps between a resume and job roles."""
    __tablename__ = "job_matches"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    job_role_id = db.Column(db.String(100), db.ForeignKey("job_roles.id"), nullable=False)
    
    match_percentage = db.Column(db.Float, nullable=False)
    tfidf_score = db.Column(db.Float, default=0.0)
    
    matched_skills_json = db.Column(db.Text, default="[]")
    missing_skills_json = db.Column(db.Text, default="[]")
    matched_preferred_skills_json = db.Column(db.Text, default="[]")
    
    job_role = db.relationship("JobRole", lazy="joined")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def matched_skills(self):
        try:
            return json.loads(self.matched_skills_json or "[]")
        except Exception:
            return []

    @matched_skills.setter
    def matched_skills(self, value):
        self.matched_skills_json = json.dumps(value)

    @property
    def missing_skills(self):
        try:
            return json.loads(self.missing_skills_json or "[]")
        except Exception:
            return []

    @missing_skills.setter
    def missing_skills(self, value):
        self.missing_skills_json = json.dumps(value)

    @property
    def matched_preferred_skills(self):
        try:
            return json.loads(self.matched_preferred_skills_json or "[]")
        except Exception:
            return []

    @matched_preferred_skills.setter
    def matched_preferred_skills(self, value):
        self.matched_preferred_skills_json = json.dumps(value)

    @property
    def job_title(self):
        if self.job_role and self.job_role.title:
            return self.job_role.title
        if self.job_role_id:
            return self.job_role_id.replace("-", " ").title()
        return "Unknown Role"

    @property
    def domain(self):
        return self.job_role.domain if self.job_role else ""

    @property
    def experience_level(self):
        return self.job_role.experience_level if self.job_role else ""

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "job_role_id": self.job_role_id,
            "job_title": self.job_title,
            "domain": self.domain,
            "experience_level": self.experience_level,
            "match_percentage": round(self.match_percentage, 1) if self.match_percentage is not None else 0.0,
            "tfidf_score": round(self.tfidf_score, 3) if self.tfidf_score is not None else 0.0,
            "matched_skills": self.matched_skills,
            "missing_skills": self.missing_skills,
            "matched_preferred_skills": self.matched_preferred_skills,
            "matched_skills_json": self.matched_skills_json,
            "missing_skills_json": self.missing_skills_json,
            "matched_preferred_skills_json": self.matched_preferred_skills_json,
        }


class Recommendation(db.Model):
    """Stores prioritized skill recommendations and learning resources for candidates."""
    __tablename__ = "recommendations"

    id = db.Column(db.Integer, primary_key=True)
    resume_id = db.Column(db.Integer, db.ForeignKey("resumes.id", ondelete="CASCADE"), nullable=False)
    skill_name = db.Column(db.String(100), nullable=False)
    target_job_role = db.Column(db.String(150), nullable=False)
    priority = db.Column(db.String(20), default="High")  # High, Medium, Low
    category = db.Column(db.String(100), default="Technical")
    resources_json = db.Column(db.Text, default="[]")

    def __init__(self, **kwargs):
        super().__init__(**kwargs)

    @property
    def resources(self):
        try:
            return json.loads(self.resources_json or "[]")
        except Exception:
            return []

    @resources.setter
    def resources(self, value):
        self.resources_json = json.dumps(value)

    def to_dict(self):
        return {
            "id": self.id,
            "resume_id": self.resume_id,
            "skill_name": self.skill_name,
            "target_job_role": self.target_job_role,
            "priority": self.priority,
            "category": self.category,
            "resources": self.resources,
        }
