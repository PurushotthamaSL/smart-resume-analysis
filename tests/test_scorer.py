from app.nlp.scorer import ResumeScorer


def test_resume_scorer_high_quality():
    scorer = ResumeScorer()
    parsed_data = {
        "name": "Jane Smith",
        "email": "jane@example.com",
        "phone": "+1 555-987-6543",
        "links": {"linkedin": "https://linkedin.com/in/janesmith"},
        "summary": "Experienced engineer with a track record of scalable systems.",
        "sections": {"experience": "...", "education": "...", "skills": "..."},
        "experience": [{"role": "Senior Engineer"}],
        "education": [{"degree": "B.S. Computer Science"}],
        "certifications": ["AWS Certified"],
        "word_count": 650,
        "raw_text": "Architected distributed systems, reduced latency by 35%, deployed 15 microservices across 200,000 users. Engineered resilient APIs."
    }
    extracted_skills = {
        "total_count": 12,
        "unique_names": ["Python", "Docker", "Kubernetes", "AWS", "SQL"]
    }

    scores = scorer.calculate_scores(parsed_data, extracted_skills)
    assert scores["completeness_score"] >= 80
    assert scores["ats_score"] >= 75
    assert len(scores["strengths"]) > 0


def test_resume_scorer_sparse():
    scorer = ResumeScorer()
    parsed_data = {
        "name": None,
        "email": None,
        "phone": None,
        "links": {},
        "summary": "",
        "sections": {},
        "experience": [],
        "education": [],
        "certifications": [],
        "word_count": 50,
        "raw_text": "Hello I am looking for a job."
    }
    extracted_skills = {
        "total_count": 0,
        "unique_names": []
    }

    scores = scorer.calculate_scores(parsed_data, extracted_skills)
    assert scores["completeness_score"] < 40
    assert scores["ats_score"] < 40
    assert len(scores["warnings"]) >= 2
