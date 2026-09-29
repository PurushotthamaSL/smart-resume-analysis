import re
from pathlib import Path
from typing import Dict, Any, List, Optional

# PDF & DOCX parsing
try:
    import pymupdf as fitz  # PyMuPDF
    HAVE_PYMUPDF = True
except ImportError:
    try:
        import fitz
        HAVE_PYMUPDF = True
    except ImportError:
        fitz = None
        HAVE_PYMUPDF = False

try:
    import pypdf
    HAVE_PYPDF = True
except ImportError:
    pypdf = None
    HAVE_PYPDF = False

try:
    import docx
    HAVE_DOCX = True
except ImportError:
    docx = None
    HAVE_DOCX = False

# spaCy loading helper
_spacy_nlp = None

def get_spacy_nlp():
    """Lazily load spaCy model or fallback gracefully."""
    global _spacy_nlp
    if _spacy_nlp is None:
        try:
            import spacy
            try:
                _spacy_nlp = spacy.load("en_core_web_sm")
            except OSError:
                # If model is not downloaded yet, load a blank english model
                _spacy_nlp = spacy.blank("en")
        except Exception:
            _spacy_nlp = None
    return _spacy_nlp


class ResumeParser:
    """
    Extracts text and structured entities from PDF and DOCX resumes:
    Name, Email, Phone, Links, Education, Experience, Certifications, and Sections.
    """

    EMAIL_REGEX = re.compile(
        r"[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+", re.IGNORECASE
    )

    PHONE_REGEX = re.compile(
        r"(?:(?:\+?\d{1,3}[-.\s]?)?(?:\(?\d{2,4}\)?[-.\s]?)?\d{3,4}[-.\s]?\d{3,4})",
        re.VERBOSE
    )

    LINKEDIN_REGEX = re.compile(r"linkedin\.com/in/([a-zA-Z0-9_-]+)", re.IGNORECASE)
    GITHUB_REGEX = re.compile(r"github\.com/([a-zA-Z0-9_-]+)", re.IGNORECASE)

    # Standard resume section headers
    SECTION_HEADERS = {
        "experience": [
            "work experience", "experience", "employment history", "professional experience",
            "work history", "career history", "internships", "relevant experience"
        ],
        "education": [
            "education", "academic background", "academics", "qualifications",
            "educational qualifications", "academic credentials"
        ],
        "skills": [
            "skills", "technical skills", "core competencies", "skills & tools",
            "technologies", "tech stack", "programming skills", "skills and expertise"
        ],
        "projects": [
            "projects", "personal projects", "academic projects", "key projects",
            "featured projects", "open source contributions"
        ],
        "certifications": [
            "certifications", "licenses & certifications", "certificates",
            "accreditations", "professional certifications"
        ],
        "summary": [
            "summary", "professional summary", "about me", "profile",
            "executive summary", "objective", "career objective"
        ],
        "awards": [
            "awards", "honors & awards", "achievements", "accomplishments",
            "publications"
        ]
    }

    DEGREE_PATTERNS = [
        r"\b(?:b\.?tech|b\.?e\.?|bachelor(?:'s)?(?:\s+of\s+science|\s+of\s+engineering|\s+of\s+arts|\s+of\s+technology)?|bs|ba)\b",
        r"\b(?:m\.?tech|m\.?s\.?|master(?:'s)?(?:\s+of\s+science|\s+of\s+engineering|\s+of\s+arts|\s+of\s+business\s+administration)?|mba|ms|ma)\b",
        r"\b(?:ph\.?d\.?|doctorate|doctor\s+of\s+philosophy)\b",
        r"\b(?:diploma|associate(?:'s)?(?:\s+degree)?)\b",
    ]

    YEAR_PATTERN = re.compile(r"\b(19\d{2}|20[0-2]\d)\b")
    DATE_RANGE_PATTERN = re.compile(
        r"\b(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(?:19\d{2}|20\d{2})\s*(?:-|–|—|to)\s*(?:(?:jan|feb|mar|apr|may|jun|jul|aug|sep|oct|nov|dec)[a-z]*\.?\s*(?:19\d{2}|20\d{2})|present|current)\b",
        re.IGNORECASE
    )

    def extract_text_from_file(self, file_path: str) -> str:
        """Extract raw plain text from PDF, DOCX, or TXT file."""
        path = Path(file_path)
        ext = path.suffix.lower()

        if not path.exists():
            raise FileNotFoundError(f"File not found: {file_path}")

        if ext == ".pdf":
            return self._extract_text_from_pdf(path)
        elif ext in [".docx", ".doc"]:
            return self._extract_text_from_docx(path)
        elif ext in [".txt", ".text"]:
            return self._extract_text_from_txt(path)
        else:
            raise ValueError(f"Unsupported file format: {ext}. Only PDF, DOCX, and TXT are supported.")

    def _extract_text_from_txt(self, path: Path) -> str:
        """Extract text from plain text file."""
        for enc in ["utf-8", "utf-8-sig", "latin-1", "cp1252"]:
            try:
                with open(path, "r", encoding=enc, errors="replace") as f:
                    content = f.read()
                if content.strip():
                    return self._clean_text(content)
            except Exception:
                continue
        raise ValueError("Text file appears to be empty or unreadable.")

    def _extract_text_from_pdf(self, path: Path) -> str:
        """Extract text using PyMuPDF (fitz) with fallback to pypdf."""
        text = ""
        if HAVE_PYMUPDF and fitz is not None:
            try:
                doc = fitz.open(str(path))
                for page in doc:
                    page_text = page.get_text()
                    if page_text:
                        text += str(page_text) + "\n"
                doc.close()
                if text.strip():
                    return self._clean_text(text)
            except Exception:
                pass  # Fallback to pypdf

        if HAVE_PYPDF and pypdf is not None:
            try:
                reader = pypdf.PdfReader(str(path))
                for page in reader.pages:
                    page_text = page.extract_text()
                    if page_text:
                        text += str(page_text) + "\n"
                if text.strip():
                    return self._clean_text(text)
            except Exception:
                pass

        # Fallback: check if the file is actually plain text
        try:
            return self._extract_text_from_txt(path)
        except Exception:
            pass

        if not text.strip():
            raise ValueError("PDF file appears to be empty, encrypted, or image-only.")
        return self._clean_text(text)

    def _extract_text_from_docx(self, path: Path) -> str:
        """Extract text from DOCX file including tables, with fallback for plain text files."""
        if HAVE_DOCX and docx is not None:
            try:
                doc = docx.Document(str(path))
                full_text = []

                for para in doc.paragraphs:
                    if para.text.strip():
                        full_text.append(para.text)

                for table in doc.tables:
                    for row in table.rows:
                        row_text = [cell.text.strip() for cell in row.cells if cell.text.strip()]
                        if row_text:
                            full_text.append(" | ".join(row_text))

                text = "\n".join(full_text)
                if text.strip():
                    return self._clean_text(text)
            except Exception:
                # If docx zip extraction fails (e.g., virtual text blob uploaded with .docx extension),
                # fallback gracefully to raw text reading
                try:
                    return self._extract_text_from_txt(path)
                except Exception:
                    pass

        # If python-docx is not installed, attempt text extraction as fallback
        try:
            return self._extract_text_from_txt(path)
        except Exception:
            pass

        raise RuntimeError("Failed to extract text from DOCX document. Ensure the file is not corrupted.")


    def _clean_text(self, text: str) -> str:
        """Normalize line breaks, remove null bytes and excessive whitespace."""
        text = text.replace("\x00", "")
        text = re.sub(r"\r\n|\r", "\n", text)
        text = re.sub(r"[ \t]+", " ", text)
        # Keep double newlines for paragraph breaks
        text = re.sub(r"\n{3,}", "\n\n", text)
        return text.strip()

    def parse(self, text: str, filename: str = "") -> Dict[str, Any]:
        """Complete parsing pipeline returning structured resume data."""
        if not text or not text.strip():
            return {
                "name": None,
                "email": None,
                "phone": None,
                "links": {},
                "summary": "",
                "sections": {},
                "education": [],
                "experience": [],
                "certifications": [],
                "raw_text": "",
                "word_count": 0,
            }

        lines = [line.strip() for line in text.split("\n") if line.strip()]
        sections = self._segment_sections(lines)
        
        email = self._extract_email(text)
        phone = self._extract_phone(text)
        links = self._extract_links(text)
        name = self._extract_name(lines, email, sections)
        
        education = self._parse_education(sections.get("education", ""), text)
        experience = self._parse_experience(sections.get("experience", ""), text)
        certifications = self._parse_certifications(sections.get("certifications", ""), text)

        summary = sections.get("summary", "")
        if not summary and len(lines) > 2:
            # Fallback to the first intro block if short
            top_lines = lines[1:5]
            summary = " ".join([l for l in top_lines if len(l) > 20 and not self.EMAIL_REGEX.search(l)])

        return {
            "name": name,
            "email": email,
            "phone": phone,
            "links": links,
            "summary": summary[:400] if summary else "",
            "sections": sections,
            "education": education,
            "experience": experience,
            "certifications": certifications,
            "raw_text": text,
            "word_count": len(text.split()),
        }

    def _extract_email(self, text: str) -> Optional[str]:
        """Extract candidate email using regex."""
        matches = self.EMAIL_REGEX.findall(text)
        if matches:
            # Filter out generic website domains if any
            for email in matches:
                lower = email.lower()
                if not any(skip in lower for skip in ["example.com", "domain.com", "yourname"]):
                    return email.strip()
            return matches[0].strip()
        return None

    def _extract_phone(self, text: str) -> Optional[str]:
        """Extract phone number and validate length (10-14 digits)."""
        matches = self.PHONE_REGEX.findall(text)
        for match in matches:
            cleaned = re.sub(r"[^\d+]", "", match)
            digits_only = re.sub(r"[^\d]", "", cleaned)
            # A valid phone number usually has between 10 and 14 digits
            if 10 <= len(digits_only) <= 14:
                return match.strip()
        return None

    def _extract_links(self, text: str) -> Dict[str, str]:
        """Extract LinkedIn, GitHub, and portfolio links."""
        links = {}
        li_match = self.LINKEDIN_REGEX.search(text)
        if li_match:
            links["linkedin"] = f"https://linkedin.com/in/{li_match.group(1)}"

        gh_match = self.GITHUB_REGEX.search(text)
        if gh_match:
            links["github"] = f"https://github.com/{gh_match.group(1)}"

        return links

    def _extract_name(self, lines: List[str], email: Optional[str] = None, sections: Optional[Dict[str, str]] = None) -> Optional[str]:
        """
        Extract candidate name:
        1. Check first 5 non-empty lines before section headers.
        2. Filter out email, phone, labels (Resume, Curriculum Vitae, Portfolio).
        3. Use spaCy NER PERSON tag if available, or title case heuristic.
        """
        ignore_words = {
            "resume", "curriculum", "vitae", "cv", "portfolio", "page", "profile",
            "contact", "summary", "experience", "education", "skills", "projects",
            "certifications", "phone", "email", "address", "linkedin", "github"
        }

        candidate_lines = []
        for line in lines[:8]:
            lower = line.lower()
            if any(h in lower for headers in self.SECTION_HEADERS.values() for h in headers):
                break
            if email and email.lower() in lower:
                continue
            if self.EMAIL_REGEX.search(line) or self.PHONE_REGEX.search(line):
                continue
            if len(line.split()) <= 4 and not any(w in lower for w in ignore_words):
                candidate_lines.append(line)

        # Check with spaCy NER first
        nlp = get_spacy_nlp()
        if nlp and candidate_lines:
            for cand in candidate_lines:
                doc = nlp(cand)
                for ent in doc.ents:
                    if ent.label_ == "PERSON" and len(ent.text.split()) >= 2:
                        return ent.text.strip()

        # Heuristic fallback: first capitalized 2-3 word string
        for cand in candidate_lines:
            words = cand.split()
            if 2 <= len(words) <= 4:
                # Check that words start with capital letter and contain only alphabets/dashes
                if all(w[0].isupper() and re.match(r"^[A-Za-z.-]+$", w) for w in words):
                    return cand.strip()

        # Fallback to the very first line if short and alphabet-based
        if candidate_lines:
            return candidate_lines[0].strip()

        return None

    def _segment_sections(self, lines: List[str]) -> Dict[str, str]:
        """Segment resume lines into standard sections."""
        sections: Dict[str, List[str]] = {}
        current_section = "intro"
        sections[current_section] = []

        for line in lines:
            normalized_line = line.lower().strip()
            # Remove punctuation like ':' or '-'
            header_candidate = re.sub(r"[:\-_#*]", "", normalized_line).strip()

            matched_header = None
            for section_name, headers in self.SECTION_HEADERS.items():
                if header_candidate in headers or any(header_candidate == h for h in headers):
                    matched_header = section_name
                    break

            if matched_header:
                current_section = matched_header
                if current_section not in sections:
                    sections[current_section] = []
            else:
                sections[current_section].append(line)

        # Join lines into strings
        return {sec: "\n".join(sec_lines).strip() for sec, sec_lines in sections.items() if sec_lines}

    def _parse_education(self, edu_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Extract degrees, institutions, and graduation years."""
        target_text = edu_text if len(edu_text.strip()) > 30 else full_text
        entries = []

        lines = [l.strip() for l in target_text.split("\n") if l.strip()]
        for line in lines:
            degree_match = None
            for pat in self.DEGREE_PATTERNS:
                m = re.search(pat, line, re.IGNORECASE)
                if m:
                    degree_match = m.group(0)
                    break

            if degree_match:
                # Find year
                year_match = self.YEAR_PATTERN.search(line)
                year = year_match.group(0) if year_match else None
                
                # Check for GPA
                gpa_match = re.search(r"\b(?:gpa|cgpa|score)[:\s]*([0-9]\.[0-9]{1,2}(?:\s*/\s*(?:4|10))?|[0-9]{1,2}\.?\d*%)", line, re.IGNORECASE)
                gpa = gpa_match.group(1) if gpa_match else None

                entries.append({
                    "raw_text": line,
                    "degree": degree_match.title(),
                    "year": year,
                    "gpa": gpa,
                })

        return entries

    def _parse_experience(self, exp_text: str, full_text: str) -> List[Dict[str, Any]]:
        """Parse work experience roles, companies, dates, and bullet points."""
        target_text = exp_text if len(exp_text.strip()) > 50 else ""
        if not target_text:
            return []

        entries = []
        lines = [l.strip() for l in target_text.split("\n") if l.strip()]
        
        current_entry: Optional[Dict[str, Any]] = None
        for line in lines:
            # Check if line contains a date range like "Jan 2021 - Present"
            date_match = self.DATE_RANGE_PATTERN.search(line)
            if date_match or (len(line.split()) <= 6 and any(title_word in line.lower() for title_word in ["developer", "engineer", "lead", "manager", "intern", "analyst", "consultant", "scientist"])):
                if current_entry:
                    entries.append(current_entry)
                current_entry = {
                    "header": line,
                    "dates": date_match.group(0) if date_match else None,
                    "bullets": []
                }
            elif current_entry:
                current_entry["bullets"].append(line)

        if current_entry:
            entries.append(current_entry)

        return entries

    def _parse_certifications(self, cert_text: str, full_text: str) -> List[str]:
        """Extract certification names."""
        target_text = cert_text if len(cert_text.strip()) > 20 else ""
        if not target_text:
            # Search full text for common certifications
            cert_keywords = ["AWS Certified", "Certified Kubernetes", "PMP", "Scrum Master", "CompTIA", "CISSP", "Azure Certified"]
            found = []
            for kw in cert_keywords:
                if kw.lower() in full_text.lower():
                    found.append(kw)
            return found

        lines = [l.strip() for l in target_text.split("\n") if l.strip()]
        certs = []
        for line in lines:
            cleaned = re.sub(r"^[-*•\d.]+\s*", "", line).strip()
            if 3 <= len(cleaned) <= 100:
                certs.append(cleaned)
        return certs
