"""Onboarding Orchestration Agent — ServiceNow + HRIS onboarding workflows."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .shared.hris_client import get_employee
from .shared.bq_client import run_query
from .shared.servicenow_client import create_ticket, get_ticket

PROJECT = "general-ak"

# Systems provisioned for each role type
_SYSTEMS_BY_ROLE: dict[str, list[str]] = {
    "technology": ["Workday", "GitHub Enterprise", "GCP Console", "Jira", "Confluence", "Slack"],
    "operations": ["Workday", "ServiceNow", "Microsoft Office 365", "Slack", "Core Banking"],
    "frontline": ["Workday", "Core Banking", "CRM", "Bloomberg Terminal", "Slack"],
    "leadership": ["Workday", "Tableau", "Microsoft Office 365", "Slack", "Board Portal", "GCP Console"],
}


def _get_onboarding_checklist(employee_id: str, role_type: str) -> list:
    """Return the onboarding checklist for a new hire based on their role type.

    Args:
        employee_id: New hire's employee ID.
        role_type: One of 'technology', 'operations', 'frontline', 'leadership'.

    Returns:
        List of onboarding task dicts with task_name, due_day, and owner.
    """
    sql = f"""
        SELECT task_name, task_description, due_day, owner, system
        FROM `{PROJECT}.hr_analytics.onboarding_tasks`
        WHERE (role_type = '{role_type}' OR role_type = 'ALL')
          AND employee_id IS NULL
        ORDER BY due_day ASC
    """
    try:
        return run_query(sql)
    except Exception:
        # Fallback to built-in checklist when BQ is unavailable
        return _builtin_checklist(role_type)


def _builtin_checklist(role_type: str) -> list:
    """Return a built-in onboarding checklist for the given role type."""
    common = [
        {"task_name": "Pre-boarding welcome email", "due_day": -3, "owner": "HR Ops", "system": "Email"},
        {"task_name": "Background verification complete", "due_day": -1, "owner": "HR Ops", "system": "BGV Provider"},
        {"task_name": "Day 1 orientation", "due_day": 0, "owner": "HR Ops", "system": "Workday"},
        {"task_name": "Laptop and equipment setup", "due_day": 0, "owner": "IT", "system": "ServiceNow"},
        {"task_name": "ID badge and access card", "due_day": 0, "owner": "Facilities", "system": "Access Control"},
        {"task_name": "Meet buddy / onboarding partner", "due_day": 1, "owner": "Manager", "system": "Calendar"},
        {"task_name": "Complete mandatory compliance training", "due_day": 7, "owner": "L&D", "system": "LMS"},
        {"task_name": "30-day check-in with HRBP", "due_day": 30, "owner": "HRBP", "system": "Workday"},
        {"task_name": "90-day performance goal setting", "due_day": 90, "owner": "Manager", "system": "Workday"},
    ]
    role_tasks = {
        "technology": [
            {"task_name": "GitHub org access", "due_day": 1, "owner": "IT", "system": "GitHub Enterprise"},
            {"task_name": "GCP project access setup", "due_day": 1, "owner": "IT", "system": "GCP"},
            {"task_name": "Code walkthrough with tech lead", "due_day": 3, "owner": "Manager", "system": "Zoom"},
        ],
        "frontline": [
            {"task_name": "AMFI/SEBI certification review", "due_day": 5, "owner": "Compliance", "system": "LMS"},
            {"task_name": "Shadow senior RM for 5 days", "due_day": 2, "owner": "Manager", "system": "CRM"},
        ],
        "operations": [
            {"task_name": "Core banking system training", "due_day": 2, "owner": "IT", "system": "Core Banking"},
        ],
        "leadership": [
            {"task_name": "Board portal access", "due_day": 1, "owner": "IT", "system": "Board Portal"},
            {"task_name": "Meet direct reports", "due_day": 2, "owner": "Manager", "system": "Calendar"},
            {"task_name": "Strategy briefing with CEO/CFO", "due_day": 5, "owner": "EA", "system": "Calendar"},
        ],
    }
    return common + role_tasks.get(role_type, [])


def _get_onboarding_status(employee_id: str) -> dict:
    """Return onboarding completion status for an existing new hire.

    Args:
        employee_id: New hire's employee ID.

    Returns:
        Dict with completed, pending, overdue tasks and completion percentage.
    """
    sql = f"""
        SELECT task_name, due_date, assigned_to, status
        FROM `{PROJECT}.hr_analytics.onboarding_tasks`
        WHERE employee_id = '{employee_id}'
        ORDER BY due_date ASC
    """
    try:
        results = run_query(sql)
    except Exception as exc:
        return {"error": str(exc), "employee_id": employee_id}

    if not results:
        return {"note": f"No onboarding tasks found for {employee_id}"}

    completed = [r for r in results if r.get("status") == "Complete"]
    pending = [r for r in results if r.get("status") in ("Pending", None)]
    overdue = [r for r in results if r.get("status") == "Overdue"]

    return {
        "employee_id": employee_id,
        "total_tasks": len(results),
        "completed": completed,
        "pending": pending,
        "overdue": overdue,
        "completion_pct": round(len(completed) / len(results) * 100, 1) if results else 0,
    }


def _raise_it_provisioning_ticket(employee_id: str, role_type: str) -> dict:
    """Raise an IT provisioning ticket in ServiceNow for a new hire.

    Automatically selects required systems based on role type.

    Args:
        employee_id: New hire's employee ID.
        role_type: One of 'technology', 'operations', 'frontline', 'leadership'.

    Returns:
        ServiceNow ticket confirmation dict.
    """
    systems = _SYSTEMS_BY_ROLE.get(role_type, _SYSTEMS_BY_ROLE["operations"])
    return create_ticket(
        short_description=f"IT Provisioning for new hire {employee_id}",
        description=(
            f"Please provision access for new hire {employee_id} to the following systems: "
            f"{', '.join(systems)}. Role type: {role_type}."
        ),
        category="IT Provisioning",
        urgency="2",
        assignment_group="IT Onboarding",
        employee_id=employee_id,
    )


def _send_welcome_message(employee_id: str, manager_email: str, start_date: str) -> dict:
    """Schedule a personalised welcome email sequence for the new hire.

    Args:
        employee_id: New hire's employee ID.
        manager_email: Manager's email for CC.
        start_date: Join date (ISO format, e.g. "2025-06-01").

    Returns:
        Email schedule confirmation dict.
    """
    emp = get_employee(employee_id)
    if "error" in emp:
        return emp
    return {
        "status": "Scheduled",
        "recipient": emp["name"],
        "start_date": start_date,
        "manager_cc": manager_email,
        "emails_scheduled": [
            {"day": -3, "template": "Pre-boarding welcome"},
            {"day": 0,  "template": "Day 1 arrival guide"},
            {"day": 7,  "template": "Week 1 check-in"},
            {"day": 30, "template": "30-day milestone survey"},
        ],
        "note": "[STUB] Email schedule confirmed (not sent in demo mode)",
    }


def create_onboarding_agent() -> Agent:
    """Create and return the Onboarding Orchestration agent."""
    return Agent(
        name="onboarding_orchestration_agent",
        model="gemini-2.5-flash",
        description=(
            "Orchestrates end-to-end onboarding for Cymbal Wealth new hires: "
            "checklists, IT provisioning tickets, welcome communications, and "
            "progress tracking. "
            "Trigger: 'Onboard employee [ID]' or "
            "'What is the status of [name]'s onboarding?'"
        ),
        instruction="""
You are the Onboarding Orchestration Agent for Cymbal Wealth.

For a NEW employee being onboarded:
1. Fetch their profile to determine role_type — use get_employee from HRIS
2. Get the onboarding checklist for that role type — use get_onboarding_checklist
3. Raise IT provisioning ticket — use raise_it_provisioning_ticket
   (always confirm which systems with the user first)
4. Schedule the welcome email sequence — use send_welcome_message
5. Return a full onboarding plan with timeline

For checking PROGRESS on an existing new hire:
1. Fetch their onboarding completion status — use get_onboarding_status
2. Highlight overdue tasks and who owns them
3. If more than 3 tasks are overdue, flag this as a risk and recommend HRBP check-in
4. Suggest what the HR Business Partner or manager should follow up on

For new hire QUESTIONS (e.g. "Where do I go on Day 1?"):
1. Answer from the onboarding checklist
2. Always include a "Who to contact" section with the relevant owner's team

Rules:
- Always confirm which systems to provision before raising an IT ticket.
- If more than 3 tasks are overdue, escalate as a risk.
- Tell the new hire who their buddy and HRBP are (from HRIS).
- Keep your response structured and easy to scan.
        """.strip(),
        tools=[
            FunctionTool(_get_onboarding_checklist),
            FunctionTool(_get_onboarding_status),
            FunctionTool(_raise_it_provisioning_ticket),
            FunctionTool(_send_welcome_message),
            FunctionTool(get_ticket),
        ],
    )


onboarding_agent = create_onboarding_agent()
