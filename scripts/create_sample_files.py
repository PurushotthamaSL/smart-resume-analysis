from pathlib import Path
import docx
import fitz

BASE_DIR = Path(__file__).resolve().parent.parent
SAMPLES_DIR = BASE_DIR / "data" / "samples"
SAMPLES_DIR.mkdir(parents=True, exist_ok=True)

FULLSTACK_TEXT = """Alex Rivera
San Francisco, CA | (555) 382-9014 | alex.rivera@example.com | linkedin.com/in/alexrivera-dev | github.com/alexrivera

PROFESSIONAL SUMMARY
Dynamic Full Stack Developer with 4+ years of experience designing and deploying scalable web applications. Proficient in JavaScript, TypeScript, React, Node.js, and Python with hands-on expertise in PostgreSQL, Docker, AWS, and RESTful API architecture.

WORK EXPERIENCE
Senior Full Stack Engineer | NovaByte Solutions | Jan 2022 - Present
- Architected and built high-concurrency microservices using Node.js, Express, and PostgreSQL, reducing API response times by 38%.
- Developed modern responsive client interfaces with React, Next.js, and Tailwind CSS, increasing user engagement by 45%.
- Implemented CI/CD pipelines with GitHub Actions and Docker, reducing deployment cycles from 2 hours to 14 minutes.
- Integrated Redis caching layer and optimized SQL queries, supporting over 250,000 daily active users with 99.9% uptime.

Software Developer | CloudWave Tech | Jun 2020 - Dec 2021
- Developed REST APIs in Python using Flask and FastAPI for data processing workloads.
- Collaborated with product designers to build intuitive dashboard components using React and HTML5/CSS3.
- Automated end-to-end unit testing with Jest and PyTest, achieving 88% test coverage across core modules.

EDUCATION
Bachelor of Science in Computer Science | University of California, Berkeley | 2020 | GPA: 3.8 / 4.0

TECHNICAL SKILLS
- Programming Languages: JavaScript, TypeScript, Python, SQL, HTML5, CSS3
- Web & Frameworks: React, Next.js, Node.js, Express.js, Flask, FastAPI, Tailwind CSS, REST API
- Databases & Storage: PostgreSQL, Redis, MySQL, MongoDB
- Cloud & DevOps: Docker, AWS, Git, CI/CD, Linux, GitHub Actions
- Software Engineering: System Design, Agile / Scrum, Clean Code, Test-Driven Development
"""

DATA_SCIENTIST_TEXT = """Dr. Priya Sharma
New York, NY | (555) 749-1123 | priya.sharma@example.com | linkedin.com/in/priyasharma-ds | github.com/priyasharma-ai

PROFESSIONAL SUMMARY
Senior Data Scientist with 5+ years of experience developing predictive machine learning models, natural language processing pipelines, and deep neural networks. Expert in Python, PyTorch, Scikit-Learn, Pandas, and big data analysis.

WORK EXPERIENCE
Lead Data Scientist | Horizon Analytics | Mar 2022 - Present
- Spearheaded development of end-to-end customer churn prediction engine using Python, Scikit-Learn, and XGBoost, saving $1.4M annually.
- Designed and trained transformer-based NLP classification models with PyTorch and Hugging Face, boosting text categorization accuracy to 94.2%.
- Built automated ETL data pipelines in SQL and PostgreSQL processing over 50M records weekly.
- Mentored a cross-functional team of 6 junior data scientists and established rigorous cross-validation and ML evaluation standards.

Data Scientist | Alpha Insights | Aug 2019 - Feb 2022
- Analyzed complex user behavioral datasets using Pandas, NumPy, and SciPy to extract key conversion insights.
- Created interactive visualization dashboards in Tableau and Matplotlib for executive leadership.
- Implemented A/B testing frameworks that optimized recommendation click-through rates by 22%.

EDUCATION
Master of Science in Data Science & Machine Learning | Columbia University | 2019 | GPA: 3.9 / 4.0
Bachelor of Technology in Computer Engineering | 2017

TECHNICAL SKILLS
- Programming Languages: Python, R, SQL, Bash
- Data Science & AI: Machine Learning, Deep Learning, NLP, PyTorch, TensorFlow, Scikit-Learn, Pandas, NumPy, Hugging Face, Matplotlib, Seaborn
- Databases & Cloud: PostgreSQL, BigQuery, AWS, Docker
- Tools & Practices: Git, Tableau, Power BI, Statistics, Problem Solving, Communication
"""

DEVOPS_TEXT = """Marcus Vance
Seattle, WA | (555) 912-4481 | marcus.vance@example.com | linkedin.com/in/marcusvance-devops | github.com/marcusvance

PROFESSIONAL SUMMARY
DevOps & Cloud Infrastructure Engineer with 6+ years of expertise in Kubernetes container orchestration, AWS cloud architecture, Infrastructure as Code (Terraform), and robust CI/CD automation pipelines.

WORK EXPERIENCE
Senior Cloud & DevOps Engineer | Apex Cloud Systems | Feb 2021 - Present
- Architected enterprise multi-region AWS cloud infrastructure utilizing Terraform, achieving 99.99% system availability.
- Orchestrated container deployments across 8 Kubernetes (EKS) production clusters managing over 400 microservices.
- Built automated CI/CD deployment pipelines using GitHub Actions and Jenkins, cutting production release failures by 65%.
- Implemented centralized monitoring and alerting infrastructure with Prometheus, Grafana, and ELK stack.

Site Reliability Engineer | Stratos Networks | Jun 2018 - Jan 2021
- Automated cloud provisioning and configuration management using Ansible and Python scripting.
- Hardened Linux servers and implemented network security compliance policies (OWASP, IAM, SSL/TLS).
- Optimized Docker container images, shrinking build footprints by 42% and speeding up deployment pipelines.

EDUCATION
Bachelor of Science in Information Technology | University of Washington | 2018

CERTIFICATIONS
- AWS Certified Solutions Architect Associate
- Certified Kubernetes Administrator (CKA)

TECHNICAL SKILLS
- Cloud & Infrastructure: AWS, Docker, Kubernetes, Terraform, Linux, Ansible, CI/CD, Nginx
- Monitoring & Scripting: Prometheus, Grafana, Bash, Python, Git
- Security & Concepts: System Design, Cybersecurity, Network Security, Microservices, Agile / Scrum
"""

def create_docx(text: str, output_path: Path):
    doc = docx.Document()
    for line in text.split("\n"):
        doc.add_paragraph(line)
    doc.save(str(output_path))
    print(f"Created DOCX: {output_path}")

def create_pdf(text: str, output_path: Path):
    doc = fitz.open()
    page = doc.new_page()
    rect = fitz.Rect(50, 50, 550, 800)
    # Insert formatted text
    page.insert_textbox(rect, text, fontsize=10, fontname="helv")
    doc.save(str(output_path))
    doc.close()
    print(f"Created PDF: {output_path}")

if __name__ == "__main__":
    create_docx(FULLSTACK_TEXT, SAMPLES_DIR / "sample_fullstack_alex_rivera.docx")
    create_pdf(DATA_SCIENTIST_TEXT, SAMPLES_DIR / "sample_datascientist_priya_sharma.pdf")
    create_pdf(DEVOPS_TEXT, SAMPLES_DIR / "sample_devops_marcus_vance.pdf")
    
    # Also save raw text files
    with open(SAMPLES_DIR / "sample_fullstack.txt", "w", encoding="utf-8") as f:
        f.write(FULLSTACK_TEXT)
    with open(SAMPLES_DIR / "sample_datascientist.txt", "w", encoding="utf-8") as f:
        f.write(DATA_SCIENTIST_TEXT)
    with open(SAMPLES_DIR / "sample_devops.txt", "w", encoding="utf-8") as f:
        f.write(DEVOPS_TEXT)
        
    print("All sample resumes created successfully in data/samples/!")
