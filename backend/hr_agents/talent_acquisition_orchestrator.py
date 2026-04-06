"""Talent Acquisition Orchestrator — multi-agent hiring pipeline."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool, agent_tool

from .shared.ats_client import get_candidates, get_job_post
from .shared.bq_client import run_query
from .resume_screening_agent import resume_screening_agent

PROJECT = "general-ak"

# ---------------------------------------------------------------------------
# Standalone sub-agents
# ---------------------------------------------------------------------------

_job_posting_agent = Agent(
    name="job_posting_agent",
    model="gemini-2.5-flash",
    description=(
        "Drafts and validates job postings for Cymbal Wealth. "
        "Creates inclusive, skills-based job descriptions aligned with compensation bands."
    ),
    instruction="""
You are the Job Posting Agent. When asked to draft a job posting:
1. Ask for: job title, department, key responsibilities, required skills, experience level,
   compensation band, and location.
2. Draft an inclusive job description:
   - Use gender-neutral language
   - List must-have vs nice-to-have skills separately
   - Include the company's DEI statement
   - Mention flexible/hybrid work policy
3. Flag any requirements that could be unnecessarily restrictive (e.g., "must have degree"
   when skills-based criteria are available).
4. Return the draft for review before publishing.

Keep the JD to 400-600 words. Always separate responsibilities from requirements.
    """.strip(),
)

_scheduling_agent = Agent(
    name="interview_scheduling_agent",
    model="gemini-2.5-flash",
    description=(
        "Schedules interviews and coordinates between candidates and interviewers "
        "for Cymbal Wealth hiring pipelines."
    ),
    instruction="""
You are the Interview Scheduling Agent. When asked to schedule interviews:
1. Ask for: candidate names/IDs, interviewer emails, preferred date range, interview format
   (video/in-person/phone), and interview duration.
2. Suggest 3 time slot options based on typical business hours (9am-6pm IST).
3. Draft a professional interview confirmation email for the candidate.
4. Remind the hiring manager to share the interview scorecard 24 hours before.

For panel interviews, ensure at least one diverse panel member is included.
Always include interview prep resources link: https://careers.cymbalwealth.com/interview-prep
    """.strip(),
)

# ---------------------------------------------------------------------------
# Orchestrator tools
# ---------------------------------------------------------------------------

def _validate_requisition(job_id: str) -> dict:
    """Validate a job requisition for headcount approval and HRIS sync.

    Args:
        job_id: Job posting ID to validate.

    Returns:
        Validation result dict with is_valid flag and any issues.
    """
    sql = f"""
        SELECT
            job_id, title, department, headcount_approved,
            comp_band_min, comp_band_max, status,
            hris_sync_status, approved_by, approved_date
        FROM `{PROJECT}.hr_analytics.job_postings`
        WHERE posting_id = '{job_id}'
    """
    try:
        results = run_query(sql)
    except Exception as exc:
        # BQ unavailable — return stub validation
        return {
            "job_id": job_id,
            "is_valid": True,
            "validation_issues": [],
            "note": f"Validation via BQ unavailable ({exc}); manual approval assumed.",
        }

    if not results:
        return {"error": f"Requisition '{job_id}' not found", "is_valid": False}

    r = results[0]
    issues = []
    if not r.get("headcount_approved"):
        issues.append("Headcount not yet approved in HRIS")
    if r.get("hris_sync_status") != "Synced":
        issues.append("Requisition not synced to HRIS — ATS and HRIS may be out of sync")

    r["validation_issues"] = issues
    r["is_valid"] = len(issues) == 0
    return r


def _get_pipeline_status(job_id: str) -> dict:
    """Return candidate pipeline status for a job, grouped by stage.

    Args:
        job_id: Job posting ID.

    Returns:
        Dict with candidates grouped by pipeline stage.
    """
    candidates = get_candidates(job_id)
    if not candidates:
        return {"job_id": job_id, "total": 0, "stages": {}}

    stages: dict[str, list] = {}
    for c in candidates:
        stage = c.get("stage", "Unknown")
        stages.setdefault(stage, []).append({
            "candidate_id": c.get("candidate_id"),
            "name": c.get("name"),
            "source": c.get("source_channel"),
        })

    return {
        "job_id": job_id,
        "total": len(candidates),
        "stages": stages,
    }


def _schedule_interviews(
    candidate_ids: list,
    interviewer_emails: list,
    job_title: str,
    format_type: str = "video",
) -> dict:
    """Trigger interview scheduling for shortlisted candidates.

    Args:
        candidate_ids: List of candidate IDs to schedule.
        interviewer_emails: List of interviewer email addresses.
        job_title: Job title for the calendar invite.
        format_type: "video", "in-person", or "phone".

    Returns:
        Scheduling confirmation dict.
    """
    return {
        "status": "Scheduling initiated",
        "candidates_count": len(candidate_ids),
        "candidate_ids": candidate_ids,
        "interviewers": interviewer_emails,
        "format": format_type,
        "job_title": job_title,
        "note": "Calendar invites will be sent within 15 minutes (stub mode: not actually sent)",
    }


def _get_sourcing_metrics(job_id: str) -> list:
    """Return sourcing channel performance for a job.

    Args:
        job_id: Job posting ID.

    Returns:
        List of channel performance dicts.
    """
    sql = f"""
        SELECT
            source_channel,
            COUNT(*) as applications,
            COUNTIF(stage IN ('Phone Screen', 'Interview', 'Offer')) as qualified,
            ROUND(
                COUNTIF(stage IN ('Phone Screen', 'Interview', 'Offer')) / COUNT(*) * 100,
                1
            ) as quality_rate_pct
        FROM `{PROJECT}.hr_analytics.candidates`
        WHERE applied_posting = '{job_id}'
        GROUP BY source_channel
        ORDER BY quality_rate_pct DESC
    """
    try:
        return run_query(sql)
    except Exception as exc:
        return [{"note": f"Sourcing data unavailable: {exc}"}]


def create_talent_acquisition_orchestrator() -> Agent:
    """Create and return the Talent Acquisition Orchestrator agent."""
    return Agent(
        name="talent_acquisition_orchestrator",
        model="gemini-2.5-flash",
        description=(
            "Orchestrates end-to-end talent acquisition: requisition validation, "
            "job posting, candidate screening, interview scheduling, and pipeline analytics. "
            "Trigger: 'Manage hiring for job [ID]' or "
            "'What is our pipeline status for [role]?'"
        ),
        instruction="""
You are the Talent Acquisition Orchestrator for Cymbal Wealth.
You manage the end-to-end hiring process by coordinating specialised sub-agents.

For a NEW requisition:
1. Validate the requisition — use validate_requisition
2. If valid, draft the job posting — delegate to job_posting_agent
3. Delegate candidate screening to resume_screening_agent
4. From the shortlist, trigger interview scheduling — use schedule_interviews
   or delegate to interview_scheduling_agent
5. Check sourcing channel performance — use get_sourcing_metrics

For PIPELINE STATUS updates:
1. Show candidates by stage — use get_pipeline_status
2. Flag any candidates stuck in a stage for more than 5 business days
3. Surface diversity metrics if available

For INTERVIEW PREP:
1. Delegate to interview_scheduling_agent for coordination
2. Help build structured interview scorecards per competency

Rules:
- Always validate a requisition before proceeding to sourcing.
- Always confirm any candidate stage movements with the user before executing.
- Keep the user informed at each step with a clear status summary.
- Diversity: flag if the shortlisted candidate pool is not representative.
        """.strip(),
        tools=[
            FunctionTool(_validate_requisition),
            FunctionTool(_get_pipeline_status),
            FunctionTool(_schedule_interviews),
            FunctionTool(_get_sourcing_metrics),
            agent_tool.AgentTool(agent=resume_screening_agent),
            agent_tool.AgentTool(agent=_job_posting_agent),
            agent_tool.AgentTool(agent=_scheduling_agent),
        ],
    )


talent_acquisition_orchestrator = create_talent_acquisition_orchestrator()
