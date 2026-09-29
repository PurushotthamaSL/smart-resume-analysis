from pathlib import Path
from app.nlp.extractor import SkillExtractor

DATA_PATH = Path(__file__).resolve().parent.parent / "data" / "skills_taxonomy.json"


def test_skill_extractor_standard():
    extractor = SkillExtractor(str(DATA_PATH))
    text = "Proficient in Python, React, Docker, and PostgreSQL with experience in AWS and Git."
    res = extractor.extract_skills(text)

    names = res["unique_names"]
    assert "Python" in names
    assert "React" in names
    assert "Docker" in names
    assert "PostgreSQL" in names
    assert "AWS" in names
    assert "Git" in names
    assert res["total_count"] >= 6


def test_skill_extractor_categories():
    extractor = SkillExtractor(str(DATA_PATH))
    text = "We use PyTorch, TensorFlow, and Scikit-Learn for machine learning and deep learning applications."
    res = extractor.extract_skills(text)

    by_cat = res["skills_by_category"]
    assert "Data Science & AI" in by_cat
    ds_skills = by_cat["Data Science & AI"]
    assert "PyTorch" in ds_skills
    assert "Scikit-Learn" in ds_skills
    assert "Machine Learning" in ds_skills


def test_skill_extractor_short_boundaries():
    extractor = SkillExtractor(str(DATA_PATH))
    # 'Go' and 'R' with programming context vs normal english words
    text = "Skills: Go programming, R language, and SQL."
    res = extractor.extract_skills(text)
    names = res["unique_names"]
    assert "Go" in names
    assert "SQL" in names

    # Should not trigger false positive on regular words like "go to the store"
    negative_text = "I like to go to the store and buy things."
    neg_res = extractor.extract_skills(negative_text)
    assert "Go" not in neg_res["unique_names"]
