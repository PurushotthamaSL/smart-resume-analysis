from pathlib import Path
from app.nlp.matcher import JobMatcher, TfidfSimilarityModel

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "job_roles.json"


def test_job_matcher_matches():
    matcher = JobMatcher(str(DATA_PATH))
    assert len(matcher.job_roles) > 0

    # Test candidate with Full Stack skills
    resume_text = "Full Stack developer building web apps with React, Node.js, Python, PostgreSQL, REST API, Git, Docker, and JavaScript."
    candidate_skills = ["JavaScript", "React", "Node.js", "Python", "REST API", "PostgreSQL", "Git", "Docker"]

    matches = matcher.match_resume(resume_text, candidate_skills, top_n=3)
    assert len(matches) > 0

    top_match = matches[0]
    # Should identify Full Stack or Backend Engineer as top match
    assert top_match["job_role_id"] in ["full-stack-developer", "backend-engineer"]
    assert top_match["match_percentage"] >= 50.0
    assert len(top_match["matched_skills"]) > 0
    assert isinstance(top_match["missing_skills"], list)


def test_tfidf_similarity_model():
    model = TfidfSimilarityModel()
    query = "Python machine learning deep learning neural networks"
    docs = [
        "Machine learning engineer using PyTorch and neural networks for AI",
        "Chef cooking Italian cuisine and pastries",
    ]
    sims = model.compute_similarities(query, docs)
    assert len(sims) == 2
    assert sims[0] > sims[1]  # Tech doc should score higher than cooking doc
