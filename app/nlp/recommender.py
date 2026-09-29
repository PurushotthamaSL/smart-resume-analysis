import json
from pathlib import Path
from typing import List, Dict, Any, Optional
from collections import Counter


class SkillRecommender:
    """
    Recommends high-priority skills to learn based on skill gaps from top matched job roles.
    Pairs each recommended skill with curated free and paid learning resources.
    """

    def __init__(self, resources_path: Optional[str] = None):
        self.resources_path = resources_path
        self.resources_by_skill: Dict[str, List[Dict[str, Any]]] = {}
        self._load_resources()

    def _load_resources(self):
        """Load curated learning resources from JSON."""
        data = None
        if self.resources_path and Path(self.resources_path).exists():
            try:
                with open(self.resources_path, "r", encoding="utf-8") as f:
                    data = json.load(f)
            except Exception as e:
                print(f"[SkillRecommender] Warning: Could not read {self.resources_path}: {e}")

        if not data:
            fallback = Path(__file__).resolve().parent.parent.parent / "data" / "learning_resources.json"
            if fallback.exists():
                try:
                    with open(fallback, "r", encoding="utf-8") as f:
                        data = json.load(f)
                except Exception:
                    data = None

        raw_list = data.get("resources", []) if data else []
        self.resources_by_skill.clear()

        for item in raw_list:
            skill = item.get("skill", "").lower().strip()
            if skill not in self.resources_by_skill:
                self.resources_by_skill[skill] = []
            self.resources_by_skill[skill].append(item)

    def recommend(self, job_matches: List[Dict[str, Any]], limit: int = 6) -> List[Dict[str, Any]]:
        """
        Synthesize skill gaps across top matched roles, prioritize by frequency and role importance,
        and attach learning resources.
        """
        if not job_matches:
            return []

        # Count frequencies of missing skills across matched roles
        gap_frequency = Counter()
        gap_roles_map: Dict[str, List[str]] = {}

        for role_match in job_matches:
            title = role_match.get("title", "")
            for skill in role_match.get("missing_skills", []):
                gap_frequency[skill] += 2  # Higher weight for required missing skills
                if skill not in gap_roles_map:
                    gap_roles_map[skill] = []
                if title not in gap_roles_map[skill]:
                    gap_roles_map[skill].append(title)

            for skill in role_match.get("missing_preferred_skills", []):
                gap_frequency[skill] += 1  # Lower weight for preferred missing skills
                if skill not in gap_roles_map:
                    gap_roles_map[skill] = []
                if title not in gap_roles_map[skill]:
                    gap_roles_map[skill].append(title)

        recommended = []
        for skill_name, freq in gap_frequency.most_common(limit):
            associated_roles = gap_roles_map.get(skill_name, [])
            priority = "High" if freq >= 3 else ("Medium" if freq == 2 else "Low")
            
            # Fetch curated resources or build dynamic fallback
            resources = self._get_resources_for_skill(skill_name)

            recommended.append({
                "skill_name": skill_name,
                "target_job_roles": associated_roles,
                "target_job_role": associated_roles[0] if associated_roles else "Target Career",
                "frequency": freq,
                "priority": priority,
                "resources": resources
            })

        return recommended

    def _get_resources_for_skill(self, skill_name: str) -> List[Dict[str, Any]]:
        """Find matching curated courses or generate high-quality fallback links."""
        key = skill_name.lower().strip()
        if key in self.resources_by_skill:
            return self.resources_by_skill[key]

        # Dynamic fallback resource links
        safe_query = skill_name.replace(" ", "+")
        return [
            {
                "skill": skill_name,
                "title": f"Official {skill_name} Documentation & Guides",
                "platform": "Developer Docs",
                "type": "Free",
                "difficulty": "All Levels",
                "url": f"https://www.google.com/search?q={safe_query}+official+documentation",
                "description": f"Explore official reference guides, architecture, and step-by-step developer tutorials for {skill_name}."
            },
            {
                "skill": skill_name,
                "title": f"Master {skill_name} on freeCodeCamp",
                "platform": "freeCodeCamp / YouTube",
                "type": "Free",
                "difficulty": "Beginner to Intermediate",
                "url": f"https://www.youtube.com/results?search_query=freeCodeCamp+{safe_query}+tutorial",
                "description": f"In-depth video walkthroughs and practical hands-on projects for mastering {skill_name}."
            },
            {
                "skill": skill_name,
                "title": f"{skill_name} Certification Courses on Coursera",
                "platform": "Coursera",
                "type": "Paid / Free Audit",
                "difficulty": "Intermediate",
                "url": f"https://www.coursera.org/search?query={safe_query}",
                "description": f"Accredited university and industry certifications for {skill_name}."
            }
        ]
