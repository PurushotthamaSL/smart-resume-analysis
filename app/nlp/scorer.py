import re
from typing import Dict, Any


class ResumeScorer:
    """
    Evaluates resume completeness and ATS (Applicant Tracking System) compatibility.
    Provides detailed scoring, section breakdown, and actionable optimization advice.
    """

    ACTION_VERBS = {
        "developed", "built", "created", "architected", "engineered", "designed",
        "implemented", "deployed", "optimized", "spearheaded", "orchestrated",
        "collaborated", "managed", "led", "enhanced", "automated", "reduced",
        "increased", "scaled", "analyzed", "delivered", "executed", "migrated",
        "refactored", "integrated", "programmed", "formulated", "established"
    }

    METRICS_REGEX = re.compile(
        r"(?:\b\d+(?:\.\d+)?%|\$\s*\d+(?:,\d+)*(?:\.\d+)?[kmb]?|\b\d+\s*(?:users|clients|engineers|teams|requests|queries|seconds|ms|qps|x)\b)",
        re.IGNORECASE
    )

    def calculate_scores(self, parsed_data: Dict[str, Any], extracted_skills: Dict[str, Any]) -> Dict[str, Any]:
        """
        Calculate completeness score, ATS friendliness score, breakdown,
        and generate prioritized recommendations.
        """
        text = parsed_data.get("raw_text", "")
        sections = parsed_data.get("sections", {})
        word_count = parsed_data.get("word_count", 0)
        skills_count = extracted_skills.get("total_count", 0)

        # 1. Calculate Completeness Score (0 - 100)
        completeness_details = {}
        completeness_score = 0.0

        # Contact Details (20 pts)
        has_name = bool(parsed_data.get("name"))
        has_email = bool(parsed_data.get("email"))
        has_phone = bool(parsed_data.get("phone"))
        contact_pts = (8 if has_email else 0) + (6 if has_phone else 0) + (6 if has_name else 0)
        completeness_details["contact_info"] = {"score": contact_pts, "max": 20, "passed": contact_pts >= 14}
        completeness_score += contact_pts

        # Work Experience (25 pts)
        has_exp = bool(parsed_data.get("experience") or sections.get("experience"))
        exp_pts = 25 if has_exp else 0
        completeness_details["work_experience"] = {"score": exp_pts, "max": 25, "passed": has_exp}
        completeness_score += exp_pts

        # Education (15 pts)
        has_edu = bool(parsed_data.get("education") or sections.get("education"))
        edu_pts = 15 if has_edu else 0
        completeness_details["education"] = {"score": edu_pts, "max": 15, "passed": has_edu}
        completeness_score += edu_pts

        # Skills (20 pts)
        if skills_count >= 8:
            skills_pts = 20
        elif skills_count >= 4:
            skills_pts = 14
        elif skills_count >= 1:
            skills_pts = 8
        else:
            skills_pts = 0
        completeness_details["skills"] = {"score": skills_pts, "max": 20, "passed": skills_pts >= 14}
        completeness_score += skills_pts

        # Projects or Certifications (10 pts)
        has_proj_cert = bool(sections.get("projects") or parsed_data.get("certifications") or sections.get("certifications"))
        proj_pts = 10 if has_proj_cert else 0
        completeness_details["projects_certifications"] = {"score": proj_pts, "max": 10, "passed": has_proj_cert}
        completeness_score += proj_pts

        # Summary / Objective (5 pts)
        has_sum = bool(parsed_data.get("summary") or sections.get("summary"))
        sum_pts = 5 if has_sum else 0
        completeness_details["professional_summary"] = {"score": sum_pts, "max": 5, "passed": has_sum}
        completeness_score += sum_pts

        # Online Profiles / Links (5 pts)
        links = parsed_data.get("links", {})
        has_links = bool(links.get("linkedin") or links.get("github"))
        link_pts = 5 if has_links else 0
        completeness_details["online_presence"] = {"score": link_pts, "max": 5, "passed": has_links}
        completeness_score += link_pts

        # 2. Calculate ATS Friendliness Score (0 - 100)
        ats_score = 0.0
        ats_details = {}

        # Standard Section Headers (25 pts)
        standard_header_count = sum(1 for sec in ["experience", "education", "skills", "projects", "summary"] if sec in sections)
        header_pts = min(25, standard_header_count * 6)
        ats_details["standard_sections"] = {"score": header_pts, "max": 25, "passed": header_pts >= 18}
        ats_score += header_pts

        # Resume Length / Word Count (20 pts)
        if 400 <= word_count <= 1100:
            length_pts = 20
        elif 250 <= word_count < 400 or 1101 <= word_count <= 1600:
            length_pts = 14
        elif word_count > 1600:
            length_pts = 8
        else:
            length_pts = 4
        ats_details["length_and_density"] = {"score": length_pts, "max": 20, "passed": length_pts >= 14}
        ats_score += length_pts

        # Action Verbs (20 pts)
        words_lower = set(re.findall(r"\b[a-z]{3,}\b", text.lower()))
        matched_verbs = list(words_lower.intersection(self.ACTION_VERBS))
        if len(matched_verbs) >= 6:
            verb_pts = 20
        elif len(matched_verbs) >= 3:
            verb_pts = 12
        elif len(matched_verbs) >= 1:
            verb_pts = 6
        else:
            verb_pts = 0
        ats_details["action_verbs"] = {"score": verb_pts, "max": 20, "passed": verb_pts >= 12, "count": len(matched_verbs)}
        ats_score += verb_pts

        # Measurable Metrics & Impact (20 pts)
        metrics_matches = self.METRICS_REGEX.findall(text)
        if len(metrics_matches) >= 4:
            metric_pts = 20
        elif len(metrics_matches) >= 2:
            metric_pts = 14
        elif len(metrics_matches) >= 1:
            metric_pts = 8
        else:
            metric_pts = 0
        ats_details["quantifiable_metrics"] = {"score": metric_pts, "max": 20, "passed": metric_pts >= 14, "count": len(metrics_matches)}
        ats_score += metric_pts

        # Contact Info Hygiene (15 pts)
        hygiene_pts = (8 if has_email else 0) + (7 if has_phone else 0)
        ats_details["contact_hygiene"] = {"score": hygiene_pts, "max": 15, "passed": hygiene_pts == 15}
        ats_score += hygiene_pts

        # 3. Generate Actionable Feedback, Strengths & Warnings
        strengths = []
        warnings = []
        recommendations = []

        if has_name and has_email and has_phone:
            strengths.append("Clear and complete contact information detected.")
        else:
            if not has_email:
                warnings.append("Missing or unparseable email address.")
            if not has_phone:
                warnings.append("Missing contact phone number.")

        if has_exp:
            strengths.append("Well-defined Work Experience section present.")
        else:
            warnings.append("No explicit Work Experience section found. ATS scanners prioritize clear employment headings.")
            recommendations.append("Add a dedicated 'Work Experience' or 'Employment History' section header.")

        if skills_count >= 8:
            strengths.append(f"Strong keyword density: {skills_count} industry skills extracted across domains.")
        elif skills_count < 4:
            warnings.append("Low technical skill count detected. ATS keyword algorithms may overlook your profile.")
            recommendations.append("Expand your 'Skills' section with targeted tools, frameworks, and programming languages.")

        if len(matched_verbs) >= 5:
            strengths.append(f"Uses impactful action verbs ({len(matched_verbs)} unique action verbs found).")
        else:
            recommendations.append("Start your experience bullet points with strong action verbs (e.g., 'Architected', 'Spearheaded', 'Optimized').")

        if len(metrics_matches) >= 3:
            strengths.append("Contains measurable business outcomes and quantifiable data points.")
        else:
            recommendations.append("Quantify your achievements using metrics, percentages, or dollar amounts (e.g., 'Reduced latency by 35%').")

        if word_count < 300:
            warnings.append(f"Resume is very brief ({word_count} words). Consider adding more project details and technical achievements.")
        elif word_count > 1500:
            warnings.append(f"Resume is quite long ({word_count} words). Aim for a concise 1-2 page format (500-1000 words).")

        return {
            "completeness_score": round(completeness_score, 1),
            "ats_score": round(ats_score, 1),
            "completeness_details": completeness_details,
            "ats_details": ats_details,
            "strengths": strengths,
            "warnings": warnings,
            "suggestions": recommendations,
            "stats": {
                "word_count": word_count,
                "reading_time_minutes": max(1, round(word_count / 200)),
                "action_verbs_found": len(matched_verbs),
                "metrics_found": len(metrics_matches),
                "skills_found": skills_count,
            }
        }
