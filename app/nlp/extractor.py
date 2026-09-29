import json
import re
from pathlib import Path
from typing import Dict, List, Any, Optional

try:
    import nltk
    from nltk.tokenize import word_tokenize
    from nltk.stem import WordNetLemmatizer
    HAVE_NLTK = True
except ImportError:
    HAVE_NLTK = False


def ensure_nltk_data():
    """Ensure required NLTK tokenizers and corpora are present, downloading quietly if missing."""
    if HAVE_NLTK:
        for pkg, target in [
            ("punkt", "tokenizers/punkt"),
            ("punkt_tab", "tokenizers/punkt_tab"),
            ("stopwords", "corpora/stopwords"),
            ("wordnet", "corpora/wordnet"),
        ]:
            try:
                nltk.data.find(target)
            except (LookupError, AttributeError):
                try:
                    nltk.download(pkg, quiet=True)
                except Exception:
                    pass


# Ensure data is present on module load
ensure_nltk_data()


class SkillExtractor:
    """
    Extracts and categorizes technical and soft skills from resume text using
    an extensive domain taxonomy, n-gram matching, regex, and lemmatization.
    """

    def __init__(self, taxonomy_path: Optional[str] = None):
        self.taxonomy_path = taxonomy_path
        self.categories: List[str] = []
        self.skills_list: List[Dict[str, Any]] = []
        
        # Lookup tables
        self.normalized_map: Dict[str, Dict[str, Any]] = {}
        self.max_ngram_len: int = 1
        
        # Strict boundary skills (e.g., 'C', 'R', 'Go') needing special patterns
        self.short_skills = {"c", "r", "go", "ci", "cd", "js", "ts", "ml", "dl", "ai", "db", "ui", "ux"}
        
        # Lemmatizer
        self.lemmatizer = None
        if HAVE_NLTK:
            ensure_nltk_data()
            try:
                self.lemmatizer = WordNetLemmatizer()
            except Exception:
                self.lemmatizer = None

        self._load_taxonomy()


    def _load_taxonomy(self):
        """Load skills taxonomy from JSON file or fallback to internal defaults."""
        data = None
        if self.taxonomy_path and Path(self.taxonomy_path).exists():
            try:
                with open(self.taxonomy_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[SkillExtractor] Warning: Could not read taxonomy file {self.taxonomy_path}: {e}")

        if not data:
            # Fallback path relative to this file
            fallback = Path(__file__).resolve().parent.parent.parent / "data" / "skills_taxonomy.json"
            if fallback.exists():
                try:
                    with open(fallback, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = None

        if data:
            self.categories = data.get("categories", [])
            self.skills_list = data.get("skills", [])
        else:
            self._load_default_skills()

        self._build_indices()

    def _load_default_skills(self):
        """Minimal fallback skills in case JSON cannot be read."""
        self.categories = ["Programming Languages", "Web & Frameworks", "Databases & Storage", "Cloud & DevOps", "Data Science & AI", "Soft Skills"]
        self.skills_list = [
            {"name": "Python", "category": "Programming Languages", "aliases": ["python3"]},
            {"name": "JavaScript", "category": "Programming Languages", "aliases": ["js"]},
            {"name": "React", "category": "Web & Frameworks", "aliases": ["reactjs"]},
            {"name": "Docker", "category": "Cloud & DevOps", "aliases": ["containers"]},
            {"name": "PostgreSQL", "category": "Databases & Storage", "aliases": ["postgres"]},
            {"name": "Machine Learning", "category": "Data Science & AI", "aliases": ["ml"]},
        ]

    def _normalize_key(self, text: str) -> str:
        """Standardize a skill string for case-insensitive and punctuation-free matching."""
        # Replace hyphens and dots with spaces for unified indexing, except c++ and c#
        t = text.lower().strip()
        if t in ["c++", "c#", ".net"]:
            return t
        t = re.sub(r"[^\w\s+#.]", " ", t)
        t = re.sub(r"\s+", " ", t).strip()
        return t

    def _build_indices(self):
        """Index skills and aliases by normalized string and determine maximum n-gram length."""
        self.normalized_map.clear()
        max_words = 1

        for skill in self.skills_list:
            name = skill["name"]
            category = skill.get("category", "General")
            
            # Map canonical name
            norm_name = self._normalize_key(name)
            self.normalized_map[norm_name] = {"name": name, "category": category}
            max_words = max(max_words, len(norm_name.split()))

            # Map aliases
            for alias in skill.get("aliases", []):
                norm_alias = self._normalize_key(alias)
                self.normalized_map[norm_alias] = {"name": name, "category": category}
                max_words = max(max_words, len(norm_alias.split()))

        self.max_ngram_len = min(max_words, 5)

    def extract_skills(self, text: str) -> Dict[str, Any]:
        """
        Extract unique skills found in the text, categorized by domain.
        Returns:
          {
            "skills": [ {"name": "Python", "category": "Programming Languages"}, ... ],
            "skills_by_category": { "Programming Languages": ["Python", ...], ... },
            "unique_names": ["Python", ...],
            "total_count": int
          }
        """
        if not text or not text.strip():
            return {
                "skills": [],
                "skills_by_category": {cat: [] for cat in self.categories},
                "unique_names": [],
                "total_count": 0,
            }

        found_skills: Dict[str, Dict[str, Any]] = {}
        cleaned_text = text.replace("\r", " ").replace("\n", " ")

        # 1. Regex search for short skills with word boundaries (avoid false positives like 'a', 'in', etc.)
        self._extract_short_boundary_skills(cleaned_text, found_skills)

        # 2. Tokenize and extract n-grams (from 1 to max_ngram_len)
        # Also create a version of text where hyphens/slashes are replaced by spaces for compound terms (e.g. Scikit-Learn -> Scikit Learn)
        spaced_text = re.sub(r"[-/]", " ", cleaned_text)
        tokens = self._tokenize(cleaned_text)
        tokens_spaced = self._tokenize(spaced_text)
        
        all_token_sequences = [tokens]
        if tokens_spaced != tokens:
            all_token_sequences.append(tokens_spaced)

        for token_seq in all_token_sequences:
            num_tokens = len(token_seq)
            for n in range(self.max_ngram_len, 0, -1):
                for i in range(num_tokens - n + 1):
                    window = token_seq[i:i + n]
                    phrase = " ".join(window).lower()
                    norm_phrase = self._normalize_key(phrase)

                    # Skip single common characters that aren't checked in short skills
                    if n == 1 and len(norm_phrase) <= 2 and norm_phrase not in ["c#", "r", "c", "js", "ts", "ai", "ml", "db"]:
                        continue

                    # Don't match generic English word 'go' unless via _extract_short_boundary_skills
                    if norm_phrase == "go":
                        continue

                    if norm_phrase in self.normalized_map:
                        skill_info = self.normalized_map[norm_phrase]
                        canonical_name = skill_info["name"]
                        if canonical_name not in found_skills:
                            found_skills[canonical_name] = {
                                "name": canonical_name,
                                "category": skill_info["category"]
                            }

                    # Also try lemmatized form if single or double word
                    if self.lemmatizer and n <= 2:
                        lemmatized_phrase = " ".join([self.lemmatizer.lemmatize(w) for w in window]).lower()
                        norm_lem = self._normalize_key(lemmatized_phrase)
                        if norm_lem != "go" and norm_lem in self.normalized_map:
                            skill_info = self.normalized_map[norm_lem]
                            canonical_name = skill_info["name"]
                            if canonical_name not in found_skills:
                                found_skills[canonical_name] = {
                                    "name": canonical_name,
                                    "category": skill_info["category"]
                                }

        # 3. Direct regex check for key symbols like C++, C#, .NET, Scikit-Learn
        symbol_patterns = [
            (r"\bC\+\+\b", "C++", "Programming Languages"),
            (r"\bC#\b", "C#", "Programming Languages"),
            (r"\b\.NET\b", "ASP.NET Core", "Web & Frameworks"),
            (r"\bCI\s*/\s*CD\b", "CI/CD", "Cloud & DevOps"),
            (r"\bREST(?:ful)?\s+APIs?\b", "REST API", "Web & Frameworks"),
            (r"\bReact\.js\b", "React", "Web & Frameworks"),
            (r"\bNode\.js\b", "Node.js", "Web & Frameworks"),
            (r"\bNext\.js\b", "Next.js", "Web & Frameworks"),
            (r"\bVue\.js\b", "Vue.js", "Web & Frameworks"),
            (r"\bScikit[- ]Learn\b|\bsklearn\b", "Scikit-Learn", "Data Science & AI"),
        ]
        for pat, canonical_name, cat in symbol_patterns:
            if re.search(pat, text, re.IGNORECASE):
                found_skills[canonical_name] = {"name": canonical_name, "category": cat}

        # Structure results by category
        by_category: Dict[str, List[str]] = {cat: [] for cat in self.categories}
        for info in found_skills.values():
            cat = info["category"]
            if cat not in by_category:
                by_category[cat] = []
            by_category[cat].append(info["name"])

        # Sort names alphabetically within categories
        for cat in by_category:
            by_category[cat].sort()

        all_skills_list = list(found_skills.values())
        all_skills_list.sort(key=lambda s: (s["category"], s["name"]))

        return {
            "skills": all_skills_list,
            "skills_by_category": by_category,
            "unique_names": sorted(list(found_skills.keys())),
            "total_count": len(found_skills),
        }

    def _tokenize(self, text: str) -> List[str]:
        """Tokenize text cleanly into words while preserving relevant programming symbols."""
        if HAVE_NLTK:
            try:
                raw_tokens = word_tokenize(text)
                return [t for t in raw_tokens if t.isalnum() or t in ["++", "#", ".", "-", "/"]]
            except Exception:
                pass
        
        # Regex tokenization fallback
        return re.findall(r"[A-Za-z0-9+#.-]+", text)

    def _extract_short_boundary_skills(self, text: str, found_skills: Dict[str, Dict[str, Any]]):
        """Handle short ambiguous skill names with precise regex patterns."""
        short_patterns = [
            (r"\b(?:programming in\s+|knowledge of\s+|using\s+|experience with\s+)?C\b(?!\+\+|#|[a-zA-Z])", "C", "Programming Languages"),
            (r"\b(?:programming in\s+|knowledge of\s+|using\s+)?R\b(?!\+\+|[a-zA-Z])(?:\s+programming|\s+language|\s+studio)?", "R", "Programming Languages"),
            (r"\bGolang\b|\bGo\s+(?:programming|developer|language|backend|code|routines?)\b", "Go", "Programming Languages"),
            (r"\bGit\b(?:\s+version control|\s+repository|\s+hub)?", "Git", "Tools & Platforms"),
            (r"\bSQL\b", "SQL", "Programming Languages"),
            (r"\bAWS\b", "AWS", "Cloud & DevOps"),
            (r"\bGCP\b", "Google Cloud Platform", "Cloud & DevOps"),
            (r"\bNLP\b", "NLP", "Data Science & AI"),
        ]

        for pat, canonical_name, cat in short_patterns:
            if re.search(pat, text, re.IGNORECASE):
                if canonical_name in ["C", "R"]:
                    context_match = re.search(rf"(?:skills|languages|technologies|proficient in|expertise in)[\s\S]{{0,100}}\b{canonical_name}\b", text, re.IGNORECASE)
                    if not context_match and not re.search(rf"\b{canonical_name}\s+(?:programming|language)\b", text, re.IGNORECASE):
                        continue
                found_skills[canonical_name] = {"name": canonical_name, "category": cat}

        # Check for standalone 'Go' in explicit skills list
        if "Go" not in found_skills:
            if re.search(r"\b(?:skills|languages|technologies|proficient in|stack)[\s\S]{0,100}\bGo\b(?!\s+(?:to|home|back|ahead|away|down|up|on|off|into))", text, re.IGNORECASE):
                found_skills["Go"] = {"name": "Go", "category": "Programming Languages"}
