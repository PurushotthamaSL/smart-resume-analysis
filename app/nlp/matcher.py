import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional

try:
    from sklearn.feature_extraction.text import TfidfVectorizer
    from sklearn.metrics.pairwise import cosine_similarity
    HAVE_SKLEARN = True
except ImportError:
    HAVE_SKLEARN = False


class BaseSimilarityModel:
    """Abstract base class for modular semantic similarity engines."""
    def compute_similarities(self, query_text: str, document_texts: List[str]) -> List[float]:
        raise NotImplementedError


class TfidfSimilarityModel(BaseSimilarityModel):
    """TF-IDF and Cosine Similarity implementation."""
    def __init__(self):
        self.vectorizer = None
        if HAVE_SKLEARN:
            self.vectorizer = TfidfVectorizer(
                stop_words="english",
                ngram_range=(1, 2),
                max_features=5000,
                token_pattern=r"(?u)\b\w+\b|[+#]"
            )

    def compute_similarities(self, query_text: str, document_texts: List[str]) -> List[float]:
        if not HAVE_SKLEARN or not query_text.strip() or not document_texts:
            # Fallback heuristic similarity
            return [self._jaccard_similarity(query_text, doc) for doc in document_texts]

        try:
            corpus = [query_text] + document_texts
            tfidf_matrix = self.vectorizer.fit_transform(corpus)
            query_vector = tfidf_matrix[0:1]
            doc_vectors = tfidf_matrix[1:]
            similarities = cosine_similarity(query_vector, doc_vectors)[0]
            return [float(sim) for sim in similarities]
        except Exception:
            return [self._jaccard_similarity(query_text, doc) for doc in document_texts]

    def _jaccard_similarity(self, text1: str, text2: str) -> float:
        words1 = set(re.findall(r"\w+", text1.lower()))
        words2 = set(re.findall(r"\w+", text2.lower()))
        if not words1 or not words2:
            return 0.0
        intersection = words1.intersection(words2)
        union = words1.union(words2)
        return len(intersection) / len(union) if union else 0.0


class JobMatcher:
    """
    Matches parsed resumes against target job roles using a composite score of:
    1. Direct Skill Overlap (Required + Preferred skills)
    2. TF-IDF & Cosine Content Similarity
    Calculates detailed skill gaps (missing skills).
    """

    def __init__(self, job_roles_path: Optional[str] = None, similarity_model: Optional[BaseSimilarityModel] = None):
        self.job_roles_path = job_roles_path
        self.job_roles: List[Dict[str, Any]] = []
        self.similarity_model = similarity_model or TfidfSimilarityModel()
        self._load_job_roles()

    def _load_job_roles(self):
        """Load job roles from JSON dataset or fallback."""
        data = None
        if self.job_roles_path and Path(self.job_roles_path).exists():
            try:
                with open(self.job_roles_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[JobMatcher] Warning: Could not read {self.job_roles_path}: {e}")

        if not data:
            fallback = Path(__file__).resolve().parent.parent.parent / "data" / "job_roles.json"
            if fallback.exists():
                try:
                    with open(fallback, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = None

        self.job_roles = data if isinstance(data, list) else []

    def set_job_roles(self, roles: List[Dict[str, Any]]):
        """Allows injecting job roles from database or external source."""
        self.job_roles = roles

    def match_resume(self, resume_text: str, candidate_skills: List[str], top_n: int = 5) -> List[Dict[str, Any]]:
        """
        Evaluate resume against all job roles and return top matches with skill gaps.
        """
        if not self.job_roles:
            return []

        # Prepare normalized set of candidate skills
        candidate_skills_norm = {s.lower().strip(): s for s in candidate_skills}

        # Build document texts for semantic similarity (title + description + required + keywords)
        job_docs = []
        for role in self.job_roles:
            req_str = " ".join(role.get("required_skills", []))
            pref_str = " ".join(role.get("preferred_skills", []))
            kw_str = " ".join(role.get("keywords", []))
            doc = f"{role.get('title', '')} {role.get('domain', '')} {role.get('description', '')} {req_str} {pref_str} {kw_str}"
            job_docs.append(doc)

        # Compute TF-IDF similarities
        tfidf_scores = self.similarity_model.compute_similarities(resume_text, job_docs)

        results = []
        for i, role in enumerate(self.job_roles):
            role_id = role.get("id", str(i))
            title = role.get("title", "Untitled Role")
            domain = role.get("domain", "General")
            req_skills = role.get("required_skills", [])
            pref_skills = role.get("preferred_skills", [])

            # Compute skill overlap
            matched_req = []
            missing_req = []
            for rs in req_skills:
                if rs.lower().strip() in candidate_skills_norm:
                    matched_req.append(rs)
                else:
                    missing_req.append(rs)

            matched_pref = []
            missing_pref = []
            for ps in pref_skills:
                if ps.lower().strip() in candidate_skills_norm:
                    matched_pref.append(ps)
                else:
                    missing_pref.append(ps)

            # Skill match ratio
            req_ratio = len(matched_req) / len(req_skills) if req_skills else 0.0
            pref_ratio = len(matched_pref) / len(pref_skills) if pref_skills else 0.0
            skill_score = (req_ratio * 0.75) + (pref_ratio * 0.25)

            # TF-IDF similarity score
            sim_score = tfidf_scores[i] if i < len(tfidf_scores) else 0.0

            # Composite match percentage (65% skill overlap + 35% semantic context)
            composite = (skill_score * 0.65) + (min(1.0, sim_score * 1.6) * 0.35)
            match_percentage = min(100.0, max(5.0, composite * 100.0))

            results.append({
                "job_role_id": role_id,
                "title": title,
                "domain": domain,
                "experience_level": role.get("experience_level", "Mid-Level"),
                "description": role.get("description", ""),
                "match_percentage": round(match_percentage, 1),
                "tfidf_score": round(sim_score, 3),
                "matched_skills": matched_req,
                "missing_skills": missing_req,
                "matched_preferred_skills": matched_pref,
                "missing_preferred_skills": missing_pref,
                "total_required_count": len(req_skills),
                "total_preferred_count": len(pref_skills),
            })

        # Sort descending by match percentage
        results.sort(key=lambda x: x["match_percentage"], reverse=True)
        return results[:top_n]
