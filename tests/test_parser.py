from app.nlp.parser import ResumeParser

SAMPLE_TEXT = """John Doe
Software Engineer
San Francisco, CA | 555-123-4567 | john.doe@example.com | linkedin.com/in/johndoe

SUMMARY
Versatile Software Engineer with 5 years of experience building web applications.

EXPERIENCE
Senior Software Engineer | Tech Corp | Jan 2021 - Present
- Architected microservices in Python and Node.js
- Reduced latency by 40% across distributed services

Software Engineer | Startup Inc | Jun 2018 - Dec 2020
- Built frontend components using React and TypeScript

EDUCATION
Bachelor of Science in Computer Science | Stanford University | 2018 | GPA: 3.8/4.0

SKILLS
Python, JavaScript, TypeScript, React, Docker, SQL, PostgreSQL, AWS

CERTIFICATIONS
AWS Certified Solutions Architect
"""


def test_resume_parser_contact_info():
    parser = ResumeParser()
    parsed = parser.parse(SAMPLE_TEXT, filename="john_doe_resume.pdf")

    assert parsed["email"] == "john.doe@example.com"
    assert "555" in parsed["phone"]
    assert parsed["name"] is not None
    assert "John" in parsed["name"]
    assert "linkedin" in parsed["links"]
    assert parsed["word_count"] > 30


def test_resume_parser_sections():
    parser = ResumeParser()
    parsed = parser.parse(SAMPLE_TEXT)
    sections = parsed["sections"]

    assert "experience" in sections
    assert "education" in sections
    assert "skills" in sections


def test_resume_parser_education_extraction():
    parser = ResumeParser()
    parsed = parser.parse(SAMPLE_TEXT)
    education = parsed["education"]

    assert len(education) >= 1
    assert "Bachelor" in education[0]["degree"]
    assert education[0]["year"] == "2018"


def test_resume_parser_empty_text():
    parser = ResumeParser()
    parsed = parser.parse("")
    assert parsed["name"] is None
    assert parsed["email"] is None
    assert parsed["word_count"] == 0
