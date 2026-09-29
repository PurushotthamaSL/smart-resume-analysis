import io
import pytest
from app import create_app
from app.models import db, JobRole, Resume, JobMatch


@pytest.fixture
def client():
    app = create_app("testing")
    with app.test_client() as client:
        with app.app_context():
            db.create_all()
            # Seed a sample role if needed
            if JobRole.query.count() == 0:
                role = JobRole(
                    id="full-stack-developer",
                    title="Full Stack Developer",
                    domain="Web",
                    description="Web engineering role",
                )
                role.required_skills = ["Python", "JavaScript", "React"]
                db.session.add(role)
                db.session.commit()
        yield client
        with app.app_context():
            db.drop_all()


def test_index_page(client):
    response = client.get("/")
    assert response.status_code == 200
    assert b"ResuMatch" in response.data or b"Resume" in response.data


def test_api_health(client):
    response = client.get("/api/health")
    assert response.status_code == 200
    data = response.get_json()
    assert data["status"] == "healthy"


def test_cors_headers(client):
    # Test preflight OPTIONS request
    response = client.open(
        "/api/health",
        method="OPTIONS",
        headers={
            "Origin": "http://localhost:3000",
            "Access-Control-Request-Method": "GET"
        }
    )
    assert response.status_code == 200
    assert "Access-Control-Allow-Origin" in response.headers

    # Test GET request with Origin
    response = client.get("/api/health", headers={"Origin": "http://localhost:5173"})
    assert response.status_code == 200
    assert response.headers.get("Access-Control-Allow-Origin") in ["*", "http://localhost:5173"]


def test_api_roles(client):
    response = client.get("/api/roles")
    assert response.status_code == 200
    roles = response.get_json()
    assert isinstance(roles, list)
    assert len(roles) >= 1

    # Also test /roles alias
    res_alias = client.get("/roles")
    assert res_alias.status_code == 200
    assert isinstance(res_alias.get_json(), list)


def test_api_analyze_text(client):
    payload = {
        "text": """
        Jane Developer
        jane@example.com | 555-901-2345
        Experience: Senior Developer at TechCorp.
        Skills: Python, React, Docker, SQL, PostgreSQL, Git, JavaScript.
        Education: B.S. in Computer Science.
        """
    }
    response = client.post("/api/analyze-text", json=payload)
    assert response.status_code == 200
    data = response.get_json()
    assert data["success"] is True
    assert data["candidate"]["email"] == "jane@example.com"
    assert "Python" in data["skills"]["unique_names"]
    assert len(data["job_matches"]) > 0

    # Also test /api/analyze alias
    res2 = client.post("/api/analyze", json=payload)
    assert res2.status_code == 200
    assert res2.get_json()["success"] is True


def test_upload_text_and_file(client):
    sample_text = (
        "Alice Smith\n"
        "alice@example.com | 555-123-4567\n"
        "Experience: Full Stack Engineer with 4 years building apps in Python and React.\n"
        "Skills: Python, React, JavaScript, SQL, Git, Docker, Flask.\n"
        "Education: Bachelor of Science in Software Engineering 2021."
    )

    # 1. Test upload via multipart text file
    data = {
        "resume": (io.BytesIO(sample_text.encode("utf-8")), "sample_resume.txt")
    }
    response = client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    assert response.status_code == 200
    res_data = response.get_json()
    assert res_data["success"] is True
    resume_id = res_data["resume_id"]
    assert resume_id is not None

    # 2. Test analysis retrieval via JSON API
    analysis_res = client.get(f"/api/analysis/{resume_id}")
    assert analysis_res.status_code == 200
    analysis_data = analysis_res.get_json()
    assert analysis_data["success"] is True
    assert analysis_data["resume"]["candidate_name"] == "Alice Smith"

    # 3. Test recommendations retrieval via JSON API
    recs_res = client.get(f"/api/recommendations/{resume_id}")
    assert recs_res.status_code == 200
    recs_data = recs_res.get_json()
    assert recs_data["success"] is True
    assert "recommendations" in recs_data


def test_upload_validation_errors(client):
    # Empty request
    res = client.post("/upload", json={}, headers={"Accept": "application/json"})
    assert res.status_code == 400
    assert res.get_json()["success"] is False

    # Short resume
    res2 = client.post("/upload", json={"text": "too short"}, headers={"Accept": "application/json"})
    assert res2.status_code == 400
    assert res2.get_json()["success"] is False


def test_view_analysis_html(client):
    sample_text = (
        "Bob Builder\n"
        "bob@example.com | 555-987-6543\n"
        "Experience: Full Stack Engineer with 5 years building apps in Python and React.\n"
        "Skills: Python, React, JavaScript, SQL, Git, Docker, Flask.\n"
        "Education: Bachelor of Science in Computer Science."
    )
    data = {
        "resume": (io.BytesIO(sample_text.encode("utf-8")), "bob_resume.txt")
    }
    upload_res = client.post(
        "/upload",
        data=data,
        content_type="multipart/form-data",
        headers={"Accept": "application/json"}
    )
    assert upload_res.status_code == 200
    resume_id = upload_res.get_json()["resume_id"]

    # Test GET /analysis/<id> HTML view rendering without JSON serialization error
    analysis_page_res = client.get(f"/analysis/{resume_id}")
    assert analysis_page_res.status_code == 200
    html = analysis_page_res.data.decode("utf-8")
    assert "window.dashboardData" in html
    assert "matches:" in html
    assert "Bob Builder" in html


def test_job_match_to_dict(client):
    with client.application.app_context():
        role = db.session.get(JobRole, "full-stack-developer")
        if not role:
            role = JobRole(
                id="test-role-unique-123",
                title="Backend Engineer",
                domain="Backend",
                experience_level="Senior",
                description="Senior backend engineer",
            )
            db.session.add(role)
            db.session.commit()
        resume = Resume(
            filename="test.txt",
            file_type="txt",
            raw_text="Test resume",
        )
        db.session.add(resume)
        db.session.commit()

        match = JobMatch(
            resume_id=resume.id,
            job_role_id=role.id,
            match_percentage=85.5,
            tfidf_score=0.742,
        )
        match.matched_skills = ["Python", "SQL"]
        match.missing_skills = ["Kafka"]
        db.session.add(match)
        db.session.commit()

        match_dict = match.to_dict()
        assert match_dict["job_title"] == role.title
        assert match_dict["domain"] == (role.domain or "")
        assert match_dict["match_percentage"] == 85.5
        assert match_dict["tfidf_score"] == 0.742
        assert match_dict["matched_skills"] == ["Python", "SQL"]
        assert match_dict["missing_skills"] == ["Kafka"]
        # Ensure all values are JSON serializable
        import json
        serialized = json.dumps(match_dict)
        assert role.title in serialized


def test_export_analysis_pdf(client):
    with client.application.app_context():
        resume = Resume(
            filename="alice_test.pdf",
            file_type="pdf",
            raw_text="Alice Walker\nalice@example.com\nPython, Docker, SQL engineer.",
            candidate_name="Alice Walker",
            candidate_email="alice@example.com",
            candidate_phone="+1 555-0199",
            completeness_score=88.0,
            ats_score=82.5,
        )
        resume.skills = [
            {"name": "Python", "category": "Programming Languages"},
            {"name": "Docker", "category": "DevOps & Cloud"},
        ]
        resume.ats_feedback = {
            "strengths": ["Clear contact details", "Relevant keywords"],
            "warnings": [],
            "suggestions": ["Include quantifiable metrics"],
            "stats": {"word_count": 450, "reading_time_minutes": 2, "action_verbs_found": 8, "metrics_found": 3}
        }
        resume.education = [{"degree": "B.S. Computer Science", "institution": "State University", "year": "2020"}]
        resume.experience = [{"title": "Software Engineer", "company": "Tech Corp", "duration": "2020-Present", "description": "Built REST APIs."}]
        db.session.add(resume)
        db.session.commit()
        resume_id = resume.id

    # Test /export endpoint produces valid PDF
    res = client.get(f"/analysis/{resume_id}/export")
    assert res.status_code == 200
    assert res.mimetype == "application/pdf"
    assert res.data.startswith(b"%PDF")
    content_disp = res.headers.get("Content-Disposition", "")
    assert "attachment" in content_disp
    assert ".pdf" in content_disp

    # Test /export-pdf alias endpoint
    res_alias = client.get(f"/analysis/{resume_id}/export-pdf")
    assert res_alias.status_code == 200
    assert res_alias.mimetype == "application/pdf"
    assert res_alias.data.startswith(b"%PDF")

    # Verify template shows 'Export PDF' and 'Delete' buttons
    html_res = client.get(f"/analysis/{resume_id}")
    assert html_res.status_code == 200
    html_text = html_res.data.decode("utf-8")
    assert "Export PDF" in html_text
    assert "fa-file-pdf" in html_text
    assert f"/analysis/{resume_id}/delete" in html_text
    assert "Delete" in html_text


def test_delete_analysis_form(client):
    with client.application.app_context():
        resume = Resume(
            filename="delete_me.pdf",
            file_type="pdf",
            raw_text="Test resume to delete",
            candidate_name="Delete Candidate",
        )
        db.session.add(resume)
        db.session.commit()
        resume_id = resume.id

    # POST to delete route
    del_res = client.post(f"/analysis/{resume_id}/delete", follow_redirects=False)
    assert del_res.status_code == 302
    assert del_res.headers["Location"].endswith("/") or del_res.headers["Location"] == "/"

    with client.application.app_context():
        assert db.session.get(Resume, resume_id) is None


def test_delete_analysis_json(client):
    with client.application.app_context():
        resume = Resume(
            filename="delete_ajax.pdf",
            file_type="pdf",
            raw_text="Test resume to delete via AJAX",
            candidate_name="Ajax Candidate",
        )
        db.session.add(resume)
        db.session.commit()
        resume_id = resume.id

    # POST with JSON / AJAX accept header
    del_res = client.post(
        f"/analysis/{resume_id}/delete",
        headers={"Accept": "application/json", "X-Requested-With": "XMLHttpRequest"}
    )
    assert del_res.status_code == 200
    json_data = del_res.get_json()
    assert json_data["success"] is True
    assert json_data["deleted_id"] == resume_id

    with client.application.app_context():
        assert db.session.get(Resume, resume_id) is None


def test_delete_api_endpoint(client):
    with client.application.app_context():
        resume = Resume(
            filename="delete_api.pdf",
            file_type="pdf",
            raw_text="Test resume for API deletion",
            candidate_name="API Delete Candidate",
        )
        db.session.add(resume)
        db.session.commit()
        resume_id = resume.id

    # DELETE /api/resumes/<id>
    del_res = client.delete(f"/api/resumes/{resume_id}")
    assert del_res.status_code == 200
    assert del_res.get_json()["success"] is True

    # Check 404 on deleting non-existent
    del_res_404 = client.delete(f"/api/resumes/{resume_id}")
    assert del_res_404.status_code == 404




