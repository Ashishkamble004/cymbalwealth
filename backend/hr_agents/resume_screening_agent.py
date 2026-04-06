"""Resume Screening Agent — Vertex AI text-embedding-005 semantic scoring."""

from __future__ import annotations

import numpy as np
import vertexai
from vertexai.language_models import TextEmbeddingModel

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .shared.ats_client import get_candidates, get_job_post, add_candidate_note

PROJECT = "general-ak"
REGION = "us-central1"

vertexai.init(project=PROJECT, location=REGION)

# Cached at module level — loading the model on every score_resume call is expensive
_embedding_model: TextEmbeddingModel | None = None


def _get_embedding_model() -> TextEmbeddingModel:
    global _embedding_model
    if _embedding_model is None:
        _embedding_model = TextEmbeddingModel.from_pretrained("text-embedding-005")
    return _embedding_model


def _cosine_similarity(v1: list[float], v2: list[float]) -> float:
    a, b = np.array(v1), np.array(v2)
    denom = np.linalg.norm(a) * np.linalg.norm(b)
    if denom == 0:
        return 0.0
    return float(np.dot(a, b) / denom)


def score_resume(resume_text: str, job_description: str, required_skills: str) -> dict:
    """Score a resume against a job description using semantic similarity.

    Combines a semantic embedding score (60%) with keyword skill matching (40%).

    Args:
        resume_text: Full text of the candidate's resume.
        job_description: Job description text.
        required_skills: Comma-separated list of required skills.

    Returns:
        Dict with total_score, semantic_match, skills_match, skills_found,
        and recommendation (SHORTLIST / REVIEW / REJECT).
    """
    embeddings = _get_embedding_model().get_embeddings([job_description, resume_text])
    jd_emb = embeddings[0].values
    resume_emb = embeddings[1].values

    semantic_score = _cosine_similarity(jd_emb, resume_emb)

    skills_list = [s.strip() for s in required_skills.split(",") if s.strip()]
    skills_found = [s for s in skills_list if s.lower() in resume_text.lower()]
    skills_score = len(skills_found) / len(skills_list) if skills_list else 0.0

    total = 0.6 * semantic_score + 0.4 * skills_score

    if total > 0.7:
        recommendation = "SHORTLIST"
    elif total > 0.5:
        recommendation = "REVIEW"
    else:
        recommendation = "REJECT"

    return {
        "total_score": round(total, 3),
        "semantic_match": round(semantic_score, 3),
        "skills_match": round(skills_score, 3),
        "skills_found": skills_found,
        "skills_missing": [s for s in skills_list if s not in skills_found],
        "recommendation": recommendation,
    }


def _get_applicant_pool(job_id: str) -> list:
    """Return all candidates in the application stage for a job.

    Args:
        job_id: Job posting ID.

    Returns:
        List of candidate dicts.
    """
    return get_candidates(job_id, stage="Application Review")


def _score_candidate(job_id: str, candidate_id: str, resume_text: str) -> dict:
    """Score a candidate's fit against the job using semantic AI.

    Args:
        job_id: Job posting ID.
        candidate_id: Candidate identifier.
        resume_text: Candidate's resume text.

    Returns:
        Scoring result with total_score and recommendation.
    """
    job = get_job_post(job_id)
    if "error" in job:
        return {"error": job["error"], "candidate_id": candidate_id}
    jd_text = job.get("notes", "") + " " + job.get("required_skills", "")
    required_skills = job.get("required_skills", "")
    result = score_resume(resume_text, jd_text, required_skills)
    result["candidate_id"] = candidate_id
    return result


def _write_screening_note(application_id: str, note: str, recruiter_user_id: str) -> dict:
    """Write a structured screening note to the candidate's ATS profile.

    Args:
        application_id: Candidate / application ID.
        note: Screening note text.
        recruiter_user_id: Recruiter's user ID for attribution.

    Returns:
        Confirmation dict.
    """
    return add_candidate_note(application_id, note, recruiter_user_id)


def create_resume_screening_agent() -> Agent:
    """Create and return the Resume Screening agent."""
    return Agent(
        name="resume_screening_agent",
        model="gemini-2.5-flash",
        description=(
            "Screens and shortlists job applicants by scoring résumé fit using "
            "semantic AI (Vertex AI text-embedding-005) and writing structured "
            "notes to the ATS. "
            "Trigger: 'Screen candidates for job [ID]' or 'Who should I shortlist for [role]?'"
        ),
        instruction="""
You are the Resume Screening & Shortlisting Agent for Cymbal Wealth.

When asked to screen candidates for a job:
1. Fetch the job requirements — use get_job_post
2. Fetch the applicant pool — use get_applicant_pool
3. Score each candidate's fit — use score_candidate for each applicant
4. Produce a ranked shortlist with rationale
5. Write a structured ATS screening note for each reviewed candidate — use write_screening_note

Output format:
## Shortlist for [Job Title] (Job ID: [ID])

### Recommended for Interview
| Rank | Candidate | Score | Skills Found | Gaps |
|------|-----------|-------|--------------|------|
| 1    | ...       | 0.82  | ...          | ...  |

### Needs Recruiter Review (score 0.50–0.70)
| Candidate | Score | Notes |
|-----------|-------|-------|

### Not Recommended
| Candidate | Score | Primary Reason |
|-----------|-------|----------------|

Rules:
- Do NOT use protected characteristics (gender, age, ethnicity) as shortlisting criteria.
- Flag if the recommended shortlist has fewer than 30% women candidates (pipeline health issue).
- Always write ATS notes for audit trail purposes — attribute them to the requesting recruiter.
- For borderline candidates (0.50–0.70), surface them for human review rather than auto-rejecting.
- Recommend at most 5 candidates for interview per role unless asked otherwise.
        """.strip(),
        tools=[
            FunctionTool(get_job_post),
            FunctionTool(_get_applicant_pool),
            FunctionTool(_score_candidate),
            FunctionTool(_write_screening_note),
        ],
    )


resume_screening_agent = create_resume_screening_agent()
