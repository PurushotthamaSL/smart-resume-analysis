// Client-side script for Drag & Drop resume upload, progress simulation, and sample loads

document.addEventListener('DOMContentLoaded', () => {
  const dropzone = document.getElementById('dropzone');
  const fileInput = document.getElementById('resume-input');
  const idleZone = document.getElementById('dropzone-idle');
  const previewZone = document.getElementById('file-preview-zone');
  const fileName = document.getElementById('file-name');
  const fileSize = document.getElementById('file-size');
  const fileIcon = document.getElementById('file-icon');
  const removeFileBtn = document.getElementById('remove-file-btn');
  const submitBtn = document.getElementById('submit-btn');
  const form = document.getElementById('resume-upload-form');
  const progressContainer = document.getElementById('progress-container');
  const progressStage = document.getElementById('progress-stage');
  const progressPercent = document.getElementById('progress-percent');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressDetail = document.getElementById('progress-detail');
  const errorBox = document.getElementById('upload-error');
  const errorText = document.getElementById('upload-error-text');

  let selectedFile = null;

  if (!dropzone || !fileInput) return;

  // Click on dropzone triggers file picker
  dropzone.addEventListener('click', (e) => {
    if (e.target !== removeFileBtn && !removeFileBtn.contains(e.target)) {
      fileInput.click();
    }
  });

  // Drag over / leave events
  ['dragenter', 'dragover'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.add('dragover');
    });
  });

  ['dragleave', 'drop'].forEach(eventName => {
    dropzone.addEventListener(eventName, (e) => {
      e.preventDefault();
      e.stopPropagation();
      dropzone.classList.remove('dragover');
    });
  });

  // Handle dropped files
  dropzone.addEventListener('drop', (e) => {
    const dt = e.dataTransfer;
    if (dt && dt.files && dt.files.length > 0) {
      handleFile(dt.files[0]);
    }
  });

  // Handle file input change
  fileInput.addEventListener('change', (e) => {
    if (e.target.files && e.target.files.length > 0) {
      handleFile(e.target.files[0]);
    }
  });

  // Remove file button
  removeFileBtn.addEventListener('click', (e) => {
    e.stopPropagation();
    resetFileInput();
  });

  function resetFileInput() {
    selectedFile = null;
    fileInput.value = '';
    previewZone.classList.add('hidden');
    idleZone.classList.remove('hidden');
    submitBtn.disabled = true;
    errorBox.classList.add('hidden');
  }

  function handleFile(file) {
    errorBox.classList.add('hidden');
    const validExtensions = ['pdf', 'docx'];
    const ext = file.name.split('.').pop().toLowerCase();

    if (!validExtensions.includes(ext)) {
      showError('Please upload a valid PDF or DOCX resume document.');
      resetFileInput();
      return;
    }

    if (file.size > 16 * 1024 * 1024) {
      showError('File size exceeds the 16MB limit. Please upload a smaller document.');
      resetFileInput();
      return;
    }

    selectedFile = file;
    fileName.textContent = file.name;
    fileSize.textContent = formatBytes(file.size);

    if (ext === 'pdf') {
      fileIcon.className = 'fa-solid fa-file-pdf text-2xl text-rose-400';
    } else {
      fileIcon.className = 'fa-solid fa-file-word text-2xl text-blue-400';
    }

    idleZone.classList.add('hidden');
    previewZone.classList.remove('hidden');
    submitBtn.disabled = false;
  }

  function showError(msg) {
    errorText.textContent = msg;
    errorBox.classList.remove('hidden');
  }

  function formatBytes(bytes) {
    if (bytes === 0) return '0 Bytes';
    const k = 1024;
    const sizes = ['Bytes', 'KB', 'MB'];
    const i = Math.floor(Math.log(bytes) / Math.log(k));
    return parseFloat((bytes / Math.pow(k, i)).toFixed(1)) + ' ' + sizes[i];
  }

  // Handle AJAX form submission with animated multi-stage progress
  form.addEventListener('submit', async (e) => {
    e.preventDefault();

    if (!selectedFile) {
      showError('Please select or drop a resume file first.');
      return;
    }

    submitBtn.disabled = true;
    progressContainer.classList.remove('hidden');
    errorBox.classList.add('hidden');

    const formData = new FormData();
    formData.append('resume', selectedFile);

    // Multi-stage progress indicator animation
    let currentStep = 0;
    const stages = [
      { pct: 20, title: 'Extracting document text...', detail: 'Unpacking layout, fonts, and raw sections...' },
      { pct: 45, title: 'Running spaCy NER & NLTK Tokenizer...', detail: 'Extracting candidate contact, education, and career milestones...' },
      { pct: 70, title: 'Scanning skills taxonomy...', detail: 'Evaluating technical domain skills against our benchmark database...' },
      { pct: 88, title: 'Simulating ATS scoring & TF-IDF match...', detail: 'Calculating keyword density, formatting hygiene, and job role fit...' },
      { pct: 98, title: 'Finalizing career recommendations...', detail: 'Assembling personalized skill pathways and resources...' },
    ];

    const progressTimer = setInterval(() => {
      if (currentStep < stages.length) {
        const stage = stages[currentStep];
        progressPercent.textContent = `${stage.pct}%`;
        progressBarFill.style.width = `${stage.pct}%`;
        progressStage.textContent = stage.title;
        progressDetail.textContent = stage.detail;
        currentStep++;
      }
    }, 450);

    try {
      const response = await fetch(form.action, {
        method: 'POST',
        headers: {
          'X-Requested-With': 'XMLHttpRequest'
        },
        body: formData
      });

      clearInterval(progressTimer);

      const result = await response.json();

      if (response.ok && result.success) {
        progressPercent.textContent = '100%';
        progressBarFill.style.width = '100%';
        progressStage.textContent = 'Analysis Complete!';
        progressDetail.textContent = 'Redirecting to your interactive dashboard...';

        setTimeout(() => {
          window.location.href = result.redirect_url;
        }, 600);
      } else {
        progressContainer.classList.add('hidden');
        submitBtn.disabled = false;
        showError(result.error || 'Failed to process resume. Please try another file.');
      }
    } catch (err) {
      clearInterval(progressTimer);
      progressContainer.classList.add('hidden');
      submitBtn.disabled = false;
      showError('Network error while uploading resume. Please try again.');
    }
  });
});

// Toggle raw text paste section
function toggleTextPaste() {
  const container = document.getElementById('paste-container');
  const chevron = document.getElementById('paste-chevron');
  if (container.classList.contains('hidden')) {
    container.classList.remove('hidden');
    chevron.classList.add('rotate-180');
  } else {
    container.classList.add('hidden');
    chevron.classList.remove('rotate-180');
  }
}

// Analyze raw pasted text using API
async function analyzePastedText() {
  const text = document.getElementById('raw-resume-text').value.trim();
  if (!text || text.length < 40) {
    alert('Please enter sufficient resume text (at least 30 characters).');
    return;
  }

  const btn = document.querySelector("button[onclick='analyzePastedText()']");
  const originalHtml = btn ? btn.innerHTML : '';
  if (btn) {
    btn.disabled = true;
    btn.innerHTML = '<i class="fa-solid fa-circle-notch fa-spin mr-1.5"></i> Analyzing...';
  }

  try {
    const formData = new FormData();
    formData.append('text', text);
    const blob = new Blob([text], { type: 'text/plain' });
    formData.append('resume', blob, 'pasted_resume.txt');

    const uploadRes = await fetch('/upload', {
      method: 'POST',
      headers: {
        'X-Requested-With': 'XMLHttpRequest',
        'Accept': 'application/json'
      },
      body: formData
    });

    const uploadData = await uploadRes.json();
    if (uploadRes.ok && uploadData.success && uploadData.redirect_url) {
      window.location.href = uploadData.redirect_url;
    } else {
      alert(uploadData.error || 'Failed to analyze resume text.');
      if (btn) {
        btn.disabled = false;
        btn.innerHTML = originalHtml;
      }
    }
  } catch (err) {
    alert('Error analyzing resume text: ' + err.message);
    if (btn) {
      btn.disabled = false;
      btn.innerHTML = originalHtml;
    }
  }
}


// Pre-defined sample resumes for immediate one-click testing
const sampleResumes = {
  fullstack: `Alex Rivera
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
- Software Engineering: System Design, Agile / Scrum, Clean Code, Test-Driven Development`,

  datascientist: `Dr. Priya Sharma
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
- Tools & Practices: Git, Tableau, Power BI, Statistics, Problem Solving, Communication`,

  devops: `Marcus Vance
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
- Security & Concepts: System Design, Cybersecurity, Network Security, Microservices, Agile / Scrum`
};

function loadSampleResume(type) {
  const content = sampleResumes[type];
  if (!content) return;

  const dropzone = document.getElementById('dropzone');
  const progressContainer = document.getElementById('progress-container');
  const progressStage = document.getElementById('progress-stage');
  const progressPercent = document.getElementById('progress-percent');
  const progressBarFill = document.getElementById('progress-bar-fill');
  const progressDetail = document.getElementById('progress-detail');

  progressContainer.classList.remove('hidden');
  progressPercent.textContent = '35%';
  progressBarFill.style.width = '35%';
  progressStage.textContent = 'Loading sample resume...';
  progressDetail.textContent = `Analyzing ${type.toUpperCase()} profile and matching benchmark roles...`;

  // Create text file and post to upload endpoint
  const blob = new Blob([content], { type: 'text/plain' });
  const file = new File([blob], `${type}_sample_resume.txt`, { type: 'text/plain' });

  const formData = new FormData();

  formData.append('resume', file);

  fetch('/upload', {
    method: 'POST',
    headers: { 'X-Requested-With': 'XMLHttpRequest' },
    body: formData
  })
  .then(res => res.json())
  .then(data => {
    if (data.success && data.redirect_url) {
      progressPercent.textContent = '100%';
      progressBarFill.style.width = '100%';
      progressStage.textContent = 'Sample Analyzed!';
      setTimeout(() => {
        window.location.href = data.redirect_url;
      }, 500);
    } else {
      alert(data.error || 'Failed to process sample resume.');
      progressContainer.classList.add('hidden');
    }
  })
  .catch(err => {
    alert('Error loading sample resume: ' + err.message);
    progressContainer.classList.add('hidden');
  });
}

/**
 * Handle deletion of an already analyzed resume from the home recent list
 */
window.handleDeleteRecentResume = function(event, target, candidateName) {
  if (event) {
    event.preventDefault();
    event.stopPropagation();
  }

  let resumeId = target;
  let name = candidateName;

  if (target && typeof target === 'object' && target.dataset) {
    resumeId = target.dataset.resumeId || target.getAttribute('data-resume-id');
    name = target.dataset.candidateName || target.getAttribute('data-candidate-name');
  }

  name = name || 'this candidate';
  if (!confirm(`Are you sure you want to delete the analyzed resume for "${name}"?\nThis will remove all associated analysis data.`)) {
    return;
  }

  fetch(`/analysis/${resumeId}/delete`, {
    method: 'POST',
    headers: {
      'Accept': 'application/json',
      'X-Requested-With': 'XMLHttpRequest'
    }
  })
  .then(res => {
    if (!res.ok) {
      throw new Error(`HTTP ${res.status}`);
    }
    return res.json();
  })
  .then(data => {
    if (data.success) {
      const card = document.getElementById(`resume-card-${resumeId}`);
      if (card) {
        card.style.transition = 'all 0.35s ease';
        card.style.opacity = '0';
        card.style.transform = 'scale(0.9)';
        setTimeout(() => {
          card.remove();
          const grid = document.getElementById('recent-resumes-grid');
          if (grid && grid.querySelectorAll('.group\\/card').length === 0) {
            const section = document.getElementById('recent-resumes-section');
            if (section) {
              section.style.transition = 'all 0.35s ease';
              section.style.opacity = '0';
              setTimeout(() => section.remove(), 350);
            }
          }
        }, 350);
      }
    } else {
      alert(data.error || 'Failed to delete resume.');
    }
  })
  .catch(err => {
    console.error('Delete error:', err);
    // Fallback: submit standard POST form
    const form = document.createElement('form');
    form.method = 'POST';
    form.action = `/analysis/${resumeId}/delete`;
    document.body.appendChild(form);
    form.submit();
  });
};

