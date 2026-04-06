"""1:1 Meeting Prep Agent — personalised agendas with OKR, feedback, and risk signals."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .shared.hris_client import get_employee
from .shared.bq_client import run_query

PROJECT = "general-ak"


def _get_okr_progress(employee_id: str) -> list:
    """Return the employee's current OKR status and progress.

    Args:
        employee_id: Employee identifier.

    Returns:
        List of OKR dicts ordered by progress ascending (lowest first).
    """
    sql = f"""
        SELECT
            okr_title,
            key_results,
            progress_pct,
            status,
            due_date,
            last_updated
        FROM `{PROJECT}.hr_analytics.okrs`
        WHERE employee_id = '{employee_id}'
          AND cycle = (SELECT MAX(cycle) FROM `{PROJECT}.hr_analytics.okrs`)
        ORDER BY progress_pct ASC
    """
    try:
        return run_query(sql)
    except Exception as exc:
        return [{"note": f"OKR data unavailable: {exc}"}]


def _get_recent_feedback(employee_id: str) -> list:
    """Return feedback received in the last 90 days.

    Args:
        employee_id: Employee identifier.

    Returns:
        List of feedback dicts (most recent first, max 10).
    """
    sql = f"""
        SELECT
            feedback_text,
            sentiment,
            submitted_by_role,
            submitted_date,
            feedback_type
        FROM `{PROJECT}.hr_analytics.feedback`
        WHERE employee_id = '{employee_id}'
          AND submitted_date >= DATE_SUB(CURRENT_DATE(), INTERVAL 90 DAY)
        ORDER BY submitted_date DESC
        LIMIT 10
    """
    try:
        return run_query(sql)
    except Exception as exc:
        return [{"note": f"Feedback data unavailable: {exc}"}]


def _get_flight_risk(employee_id: str) -> dict:
    """Return the employee's attrition risk level and top drivers.

    IMPORTANT: Returns risk_level (Low/Medium/High) only — the numeric
    score is never exposed outside this function.

    Args:
        employee_id: Employee identifier.

    Returns:
        Dict with risk_level, top_drivers, and recommended_intervention.
    """
    sql = f"""
        SELECT
            risk_level,
            top_driver_1, top_driver_2, top_driver_3,
            recommended_intervention
        FROM `{PROJECT}.hr_analytics.attrition_predictions`
        WHERE employee_id = '{employee_id}'
        ORDER BY prediction_date DESC
        LIMIT 1
    """
    try:
        results = run_query(sql)
    except Exception as exc:
        return {"risk_level": "Unknown", "top_drivers": [], "note": str(exc)}

    if results:
        r = results[0]
        return {
            "risk_level": r["risk_level"],
            "top_drivers": [r["top_driver_1"], r["top_driver_2"], r["top_driver_3"]],
            "recommended_intervention": r["recommended_intervention"],
        }
    return {"risk_level": "Unknown", "top_drivers": [], "recommended_intervention": None}


def create_meeting_prep_agent() -> Agent:
    """Create and return the 1:1 Meeting Prep agent."""
    return Agent(
        name="one_on_one_meeting_prep_agent",
        model="gemini-2.5-flash",
        description=(
            "Prepares personalised 1:1 meeting agendas for managers by pulling an "
            "employee's OKR progress, recent feedback, and retention risk signals. "
            "Trigger: 'Prepare my 1:1 with [name/ID]' or "
            "'What should I discuss with [name] this week?'"
        ),
        instruction="""
You are the 1:1 Meeting Prep Agent for Cymbal Wealth managers and HRBPs.

When a manager asks to prepare for a 1:1, gather the following in order:
1. Employee profile (role, tenure, team) — use get_employee
2. OKR progress — use get_okr_progress, highlight OKRs below 50% progress
3. Recent feedback themes — use get_recent_feedback
4. Retention risk level — use get_flight_risk (show level only, never the numeric score)

Then produce a structured agenda in this format:

## 1:1 Agenda: [Employee Name] — [Today's Date]

### Check-in (5 min)
- [Personalised opening question based on tenure/role]

### OKR Review (10 min)
- [List each OKR with progress %; flag those behind schedule]
- Suggested question: [coaching question for each lagging OKR]

### Feedback Discussion (5 min)
- Key themes: [summarise sentiment and themes]
- Suggested question: [coaching question]

### Development & Wellbeing (5 min)
[If risk_level is Medium or High, include retention-focused talking points
naturally — do NOT mention "flight risk" or "attrition model".]

### Next Steps
- [Actions and follow-ups from this 1:1]

Rules:
- Never mention "attrition risk score", "flight risk model", or any numeric risk score.
- If risk is High, include a development/career conversation prompt framed naturally.
- Keep the agenda to one page.
- Always include the employee's name and today's date in the heading.
        """.strip(),
        tools=[
            FunctionTool(get_employee),
            FunctionTool(_get_okr_progress),
            FunctionTool(_get_recent_feedback),
            FunctionTool(_get_flight_risk),
        ],
    )


meeting_prep_agent = create_meeting_prep_agent()
