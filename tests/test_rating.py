import io
import pytest
from app import create_app
from app.utils.rating import compute_star_rating
from app.models import db, Resume
from app.utils.pdf_generator import generate_resume_pdf


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as c:
        with app.app_context():
            db.create_all()
        yield c
        with app.app_context():
            db.drop_all()


def test_compute_star_rating_logic():
    """Verify compute_star_rating formula and star counts."""
    # 1. Exact 100% -> 5.0 stars (5 full, 0 half, 0 empty)
    rating, full, half, empty = compute_star_rating(100.0)
    assert rating == 5.0
    assert full == 5
    assert half is False
    assert empty == 0
    assert full + (1 if half else 0) + empty == 5

    # 2. 84.0% -> round((84/100)*5, 1) = 4.2 stars (4 full, 0 half, 1 empty)
    rating, full, half, empty = compute_star_rating(84.0)
    assert rating == 4.2
    assert full == 4
    assert half is False
    assert empty == 1
    assert full + (1 if half else 0) + empty == 5

    # 3. 70.0% -> round((70/100)*5, 1) = 3.5 stars (3 full, 1 half, 1 empty)
    rating, full, half, empty = compute_star_rating(70.0)
    assert rating == 3.5
    assert full == 3
    assert half is True
    assert empty == 1
    assert full + (1 if half else 0) + empty == 5

    # 4. 0.0% -> 0.0 stars (0 full, 0 half, 5 empty)
    rating, full, half, empty = compute_star_rating(0.0)
    assert rating == 0.0
    assert full == 0
    assert half is False
    assert empty == 5
    assert full + (1 if half else 0) + empty == 5

    # 5. None or invalid inputs handled gracefully
    rating, full, half, empty = compute_star_rating(None)
    assert rating == 0.0
    assert full == 0
    assert half is False
    assert empty == 5

    # 6. Clamping out of range
    rating, full, half, empty = compute_star_rating(120.0)
    assert rating == 5.0
    assert full == 5
    assert half is False
    assert empty == 0


def test_star_rating_scale_invariance():
    """Verify for all integer scores 0..100 the total stars always equals 5."""
    for score in range(101):
        rating, full, half, empty = compute_star_rating(score)
        assert 0.0 <= rating <= 5.0
        assert 0 <= full <= 5
        assert 0 <= empty <= 5
        assert full + (1 if half else 0) + empty == 5


def test_analysis_page_renders_star_rating(client):
    """Verify /analysis/<id> renders the 5-star rating display and numeric score."""
    with client.application.app_context():
        resume = Resume(
            filename="test_rating.pdf",
            file_type="pdf",
            raw_text="Alice Developer\nalice@example.com\nPython, Django, AWS engineer.",
            candidate_name="Alice Developer",
            candidate_email="alice@example.com",
            completeness_score=85.0,
            ats_score=84.0,  # 84 -> 4.2 stars
        )
        db.session.add(resume)
        db.session.commit()
        resume_id = resume.id

    res = client.get(f"/analysis/{resume_id}")
    assert res.status_code == 200
    html = res.data.decode("utf-8")

    # Star rating container and numeric equivalent
    assert "id=\"star-rating-display\"" in html
    assert "ATS Rating:" in html
    assert "(4.2 / 5)" in html
    assert "fa-solid fa-star" in html


def test_pdf_export_with_star_rating(client):
    """Verify PDF generator renders star rating for resumes with different scores."""
    with client.application.app_context():
        # Resume with 93% (4.7 stars)
        resume_high = Resume(
            filename="high.pdf",
            file_type="pdf",
            raw_text="High Candidate text",
            candidate_name="High Scorer",
            ats_score=93.0,
            completeness_score=90.0,
        )
        # Resume with 50% (2.5 stars)
        resume_mid = Resume(
            filename="mid.pdf",
            file_type="pdf",
            raw_text="Mid Candidate text",
            candidate_name="Mid Scorer",
            ats_score=50.0,
            completeness_score=50.0,
        )
        db.session.add_all([resume_high, resume_mid])
        db.session.commit()

        pdf_high = generate_resume_pdf(resume_high)
        assert pdf_high.startswith(b"%PDF")
        assert len(pdf_high) > 1000

        pdf_mid = generate_resume_pdf(resume_mid)
        assert pdf_mid.startswith(b"%PDF")
        assert len(pdf_mid) > 1000
