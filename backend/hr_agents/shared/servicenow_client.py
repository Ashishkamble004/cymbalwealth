"""ServiceNow stub — ticket creation and lookup for HR onboarding workflows."""

from __future__ import annotations

import os
import uuid
from datetime import datetime

# In-memory ticket store for demo mode
_TICKETS: dict[str, dict] = {}


def _real_mode_headers() -> tuple[str, str] | None:
    """Return (base_url, auth_header) for real ServiceNow calls, or None in stub mode."""
    base_url = os.environ.get("SERVICENOW_BASE_URL")
    if not base_url:
        return None
    from .auth import get_secret
    project_id = os.environ.get("GCP_PROJECT_ID", "general-ak")
    token = get_secret("servicenow-token", project_id)
    return base_url, f"Bearer {token}"


def create_ticket(
    short_description: str,
    description: str,
    category: str = "HR",
    urgency: str = "3",
    assignment_group: str = "HR Operations",
    employee_id: str | None = None,
) -> dict:
    """Create a ServiceNow ticket.

    In stub mode (no SERVICENOW_BASE_URL env var) the ticket is stored
    in memory and a synthetic ticket number is returned.

    Args:
        short_description: One-line summary.
        description: Full ticket body.
        category: Ticket category.
        urgency: 1 (Critical) – 4 (Low).
        assignment_group: Team that owns the ticket.
        employee_id: Optional employee reference.

    Returns:
        Dict with ticket_number, sys_id, and status.
    """
    conn = _real_mode_headers()
    if conn is None:
        ticket_id = f"STASK{10000 + len(_TICKETS) + 1}"
        sys_id = str(uuid.uuid4())
        ticket = {
            "ticket_number": ticket_id,
            "sys_id": sys_id,
            "short_description": short_description,
            "description": description,
            "category": category,
            "urgency": urgency,
            "assignment_group": assignment_group,
            "employee_id": employee_id,
            "status": "Open",
            "created_at": datetime.utcnow().isoformat(),
            "_stub": True,
        }
        _TICKETS[ticket_id] = ticket
        return {"ticket_number": ticket_id, "sys_id": sys_id, "status": "Created"}

    import requests
    base_url, auth_header = conn
    url = f"{base_url}/api/now/table/sc_request"
    payload = {
        "short_description": short_description,
        "description": description,
        "category": category,
        "urgency": urgency,
        "assignment_group": assignment_group,
    }
    resp = requests.post(
        url,
        json=payload,
        headers={"Authorization": auth_header, "Content-Type": "application/json"},
        timeout=10,
    )
    resp.raise_for_status()
    result = resp.json()["result"]
    return {"ticket_number": result["number"], "sys_id": result["sys_id"], "status": "Created"}


def get_ticket(ticket_number: str) -> dict:
    """Fetch a ServiceNow ticket by number.

    Args:
        ticket_number: Ticket number (e.g. "STASK10001").

    Returns:
        Ticket dict or error dict.
    """
    conn = _real_mode_headers()
    if conn is None:
        ticket = _TICKETS.get(ticket_number)
        if ticket is None:
            return {"error": f"Ticket '{ticket_number}' not found (stub mode)"}
        return ticket

    import requests
    base_url, auth_header = conn
    url = f"{base_url}/api/now/table/sc_request"
    resp = requests.get(
        url,
        params={"sysparm_query": f"number={ticket_number}", "sysparm_limit": 1},
        headers={"Authorization": auth_header},
        timeout=10,
    )
    resp.raise_for_status()
    results = resp.json().get("result", [])
    return results[0] if results else {"error": f"Ticket '{ticket_number}' not found"}
