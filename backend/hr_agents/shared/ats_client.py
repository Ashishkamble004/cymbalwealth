"""Greenhouse ATS stub — returns synthetic candidate data for demo purposes."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Demo candidate pool
# ---------------------------------------------------------------------------
DEMO_CANDIDATES: dict[str, dict] = {
    "CAND001": {
        "name": "Aditya Kumar",
        "email": "aditya.kumar@email.com",
        "resume_text": (
            "Senior Software Engineer with 6 years of experience in Python, "
            "Go, and distributed systems. Led migration of monolith to microservices "
            "at Infosys. Proficient in Kubernetes, GCP, and BigQuery. "
            "B.Tech Computer Science, IIT Bombay."
        ),
        "skills": ["Python", "Go", "Kubernetes", "GCP", "BigQuery", "microservices"],
        "experience_years": 6,
        "applied_posting": "JOB-2025-001",
        "stage": "Application Review",
        "source_channel": "LinkedIn",
    },
    "CAND002": {
        "name": "Nisha Patel",
        "email": "nisha.patel@email.com",
        "resume_text": (
            "Full Stack Developer with 4 years experience in React, Node.js, "
            "and PostgreSQL. Worked at Wipro on banking applications. "
            "Familiar with REST APIs and agile methodologies. B.E. from BITS Pilani."
        ),
        "skills": ["React", "Node.js", "PostgreSQL", "REST APIs", "JavaScript"],
        "experience_years": 4,
        "applied_posting": "JOB-2025-001",
        "stage": "Application Review",
        "source_channel": "Naukri",
    },
    "CAND003": {
        "name": "Sanjay Mehta",
        "email": "sanjay.mehta@email.com",
        "resume_text": (
            "Risk Analyst with 5 years experience in credit risk modeling, "
            "Basel III compliance, and stress testing. Proficient in Python, R, "
            "and SAS. MBA Finance from IIM Ahmedabad. CFA Level 2 candidate."
        ),
        "skills": ["Python", "R", "SAS", "credit risk", "Basel III", "stress testing"],
        "experience_years": 5,
        "applied_posting": "JOB-2025-002",
        "stage": "Application Review",
        "source_channel": "Referral",
    },
    "CAND004": {
        "name": "Pooja Bhatt",
        "email": "pooja.bhatt@email.com",
        "resume_text": (
            "Experienced Relationship Manager with 7 years managing HNI clients "
            "at HDFC Private Banking. Strong track record in AUM growth and client "
            "retention. Certified Financial Planner (CFP). MBA from SP Jain."
        ),
        "skills": ["wealth management", "client relationship", "AUM", "financial planning", "CFP"],
        "experience_years": 7,
        "applied_posting": "JOB-2025-003",
        "stage": "Application Review",
        "source_channel": "LinkedIn",
    },
    "CAND005": {
        "name": "Ravi Shankar",
        "email": "ravi.shankar@email.com",
        "resume_text": (
            "Junior developer with 1 year internship experience. "
            "Basic knowledge of Python and Java. Recent graduate."
        ),
        "skills": ["Python", "Java"],
        "experience_years": 1,
        "applied_posting": "JOB-2025-001",
        "stage": "Application Review",
        "source_channel": "Campus",
    },
}


def get_candidates(job_id: str, stage: str | None = None) -> list[dict]:
    """Return candidates for a given job posting.

    Args:
        job_id: Job posting ID.
        stage: Optional stage filter (e.g. "Application Review").

    Returns:
        List of candidate dicts.
    """
    results = [
        {"candidate_id": cid, **cand}
        for cid, cand in DEMO_CANDIDATES.items()
        if cand["applied_posting"] == job_id
    ]
    if stage:
        results = [c for c in results if c.get("stage") == stage]
    return results


def get_candidate(candidate_id: str) -> dict:
    """Fetch a single candidate record.

    Args:
        candidate_id: Candidate identifier.

    Returns:
        Candidate dict or error dict.
    """
    record = DEMO_CANDIDATES.get(candidate_id.upper())
    if record is None:
        return {"error": f"Candidate '{candidate_id}' not found"}
    return {"candidate_id": candidate_id, **record}


def get_job_post(job_id: str) -> dict:
    """Return stub job post details.

    Args:
        job_id: Job posting ID.

    Returns:
        Job post dict.
    """
    posts = {
        "JOB-2025-001": {
            "job_id": "JOB-2025-001",
            "title": "Senior Software Engineer",
            "department": "Engineering",
            "notes": (
                "Looking for a senior engineer with strong Python/Go skills, "
                "cloud-native experience on GCP, distributed systems expertise, "
                "and 5+ years building scalable financial services applications."
            ),
            "required_skills": "Python, Go, GCP, Kubernetes, BigQuery, microservices",
            "experience_required": 5,
            "status": "Open",
        },
        "JOB-2025-002": {
            "job_id": "JOB-2025-002",
            "title": "Risk Analyst",
            "department": "Risk",
            "notes": (
                "Risk analyst for credit risk and regulatory reporting. "
                "Must have Basel III knowledge, Python/R for modeling, 3+ years experience."
            ),
            "required_skills": "Python, R, credit risk, Basel III, stress testing",
            "experience_required": 3,
            "status": "Open",
        },
        "JOB-2025-003": {
            "job_id": "JOB-2025-003",
            "title": "Relationship Manager",
            "department": "Wealth Management",
            "notes": (
                "HNI wealth relationship manager to grow AUM and provide "
                "personalised financial planning. CFP preferred, 4+ years in private banking."
            ),
            "required_skills": "wealth management, AUM, financial planning, CFP, client relationship",
            "experience_required": 4,
            "status": "Open",
        },
    }
    post = posts.get(job_id)
    if post is None:
        return {"error": f"Job '{job_id}' not found"}
    return post


def move_candidate_stage(application_id: str, to_stage: str) -> dict:
    """Stub: move a candidate to a new pipeline stage.

    Args:
        application_id: Candidate ID.
        to_stage: Target stage name.

    Returns:
        Confirmation dict.
    """
    return {
        "application_id": application_id,
        "status": "moved",
        "to_stage": to_stage,
        "note": "[STUB] Stage movement recorded (not persisted in demo mode)",
    }


def add_candidate_note(application_id: str, note: str, user_id: str) -> dict:
    """Stub: add a screening note to a candidate's ATS profile.

    Args:
        application_id: Candidate ID.
        note: The note text.
        user_id: Recruiter's user ID.

    Returns:
        Confirmation dict.
    """
    return {
        "application_id": application_id,
        "note_added": True,
        "added_by": user_id,
        "note_preview": note[:120] + ("..." if len(note) > 120 else ""),
        "note": "[STUB] Note recorded (not persisted in demo mode)",
    }
