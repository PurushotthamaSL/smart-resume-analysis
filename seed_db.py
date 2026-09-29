import json
from pathlib import Path
from app import create_app
from app.models import db, JobRole, Resume, JobMatch, Recommendation
from app.nlp import ResumeParser, SkillExtractor, ResumeScorer, JobMatcher, SkillRecommender

BASE_DIR = Path(__file__).resolve().parent

def seed_database():
    """Seeds benchmark job roles and demo resumes into SQLite database."""
    app = create_app("development")

    with app.app_context():
        print("[1/3] Creating all SQLite database tables...")
        db.create_all()

        print("[2/3] Seeding benchmark job roles from data/job_roles.json...")
        roles_path = BASE_DIR / "data" / "job_roles.json"
        if not roles_path.exists():
            print(f"Error: {roles_path} not found.")
            return

        with open(roles_path, "r", encoding="utf-8") as f:
            roles_data = json.load(f)

        existing_roles = {r.id for r in JobRole.query.all()}
        added_roles = 0
        for item in roles_data:
            role_id = item.get("id")
            if role_id not in existing_roles:
                role = JobRole(
                    id=role_id,
                    title=item.get("title"),
                    domain=item.get("domain"),
                    experience_level=item.get("experience_level", "Mid-Level"),
                    description=item.get("description", ""),
                )
                role.required_skills = item.get("required_skills", [])
                role.preferred_skills = item.get("preferred_skills", [])
                role.keywords = item.get("keywords", [])
                db.session.add(role)
                added_roles += 1

        db.session.commit()
        print(f"-> Seeded {added_roles} new job roles (Total active: {JobRole.query.count()}).")

        # 3. Seed Sample Resumes if database has no resumes
        if Resume.query.count() == 0:
            print("[3/3] Parsing and seeding demo resumes into database...")
            samples_dir = BASE_DIR / "data" / "samples"
            sample_files = [
                samples_dir / "sample_fullstack_alex_rivera.docx",
                samples_dir / "sample_datascientist_priya_sharma.pdf",
                samples_dir / "sample_devops_marcus_vance.pdf",
            ]

            parser = ResumeParser()
            extractor = SkillExtractor(str(BASE_DIR / "data" / "skills_taxonomy.json"))
            scorer = ResumeScorer()
            all_roles = [r.to_dict() for r in JobRole.query.all()]
            matcher = JobMatcher(str(roles_path))
            matcher.set_job_roles(all_roles)
            recommender = SkillRecommender(str(BASE_DIR / "data" / "learning_resources.json"))

            for sample_path in sample_files:
                if not sample_path.exists():
                    continue

                print(f"   Processing sample: {sample_path.name}...")
                raw_text = parser.extract_text_from_file(str(sample_path))
                parsed = parser.parse(raw_text, filename=sample_path.name)
                skills = extractor.extract_skills(raw_text)
                scores = scorer.calculate_scores(parsed, skills)
                matches = matcher.match_resume(raw_text, skills["unique_names"], top_n=5)
                recs = recommender.recommend(matches, limit=6)

                resume_record = Resume(
                    filename=sample_path.name,
                    file_type=sample_path.suffix.lstrip(".").lower(),
                    file_size=sample_path.stat().st_size,
                    raw_text=raw_text,
                    candidate_name=parsed.get("name") or "Candidate",
                    candidate_email=parsed.get("email"),
                    candidate_phone=parsed.get("phone"),
                    completeness_score=scores.get("completeness_score", 0.0),
                    ats_score=scores.get("ats_score", 0.0),
                )
                resume_record.education = parsed.get("education", [])
                resume_record.experience = parsed.get("experience", [])
                resume_record.certifications = parsed.get("certifications", [])
                resume_record.skills = skills.get("skills", [])
                resume_record.ats_feedback = scores

                db.session.add(resume_record)
                db.session.flush()

                for m in matches:
                    jm = JobMatch(
                        resume_id=resume_record.id,
                        job_role_id=m["job_role_id"],
                        match_percentage=m["match_percentage"],
                        tfidf_score=m["tfidf_score"],
                    )
                    jm.matched_skills = m["matched_skills"]
                    jm.missing_skills = m["missing_skills"]
                    jm.matched_preferred_skills = m["matched_preferred_skills"]
                    db.session.add(jm)

                for r in recs:
                    rec_entry = Recommendation(
                        resume_id=resume_record.id,
                        skill_name=r["skill_name"],
                        target_job_role=r["target_job_role"],
                        priority=r["priority"],
                    )
                    rec_entry.resources = r["resources"]
                    db.session.add(rec_entry)

            db.session.commit()
            print(f"-> Seeded {Resume.query.count()} sample candidates with full NLP analysis & recommendations.")
        else:
            print("[3/3] Resumes already exist in database, skipping sample seeding.")

        print("\nDatabase initialization complete! You can now start the application with 'python run.py'.")

if __name__ == "__main__":
    seed_database()
