"""Workday HRIS stub — returns synthetic employee data for demo purposes."""

from __future__ import annotations

# ---------------------------------------------------------------------------
# Demo data — 10 realistic employees for Cymbal Wealth (India-based FSI)
# ---------------------------------------------------------------------------
DEMO_EMPLOYEES: dict[str, dict] = {
    "EMP001": {
        "name": "Priya Sharma",
        "department": "Engineering",
        "role": "Senior Software Engineer",
        "level": "L5",
        "manager": "EMP010",
        "tenure_years": 3,
        "performance_rating": 4.2,
        "salary": 1_800_000,
        "location": "Mumbai",
        "status": "Active",
        "role_type": "technology",
        "email": "priya.sharma@cymbalwealth.com",
    },
    "EMP002": {
        "name": "Rahul Verma",
        "department": "Risk",
        "role": "Risk Analyst",
        "level": "L4",
        "manager": "EMP011",
        "tenure_years": 7,
        "performance_rating": 3.8,
        "salary": 2_200_000,
        "location": "Delhi",
        "status": "Active",
        "role_type": "operations",
        "email": "rahul.verma@cymbalwealth.com",
    },
    "EMP003": {
        "name": "Ananya Iyer",
        "department": "Wealth Management",
        "role": "Relationship Manager",
        "level": "L4",
        "manager": "EMP012",
        "tenure_years": 5,
        "performance_rating": 4.5,
        "salary": 2_500_000,
        "location": "Bangalore",
        "status": "Active",
        "role_type": "frontline",
        "email": "ananya.iyer@cymbalwealth.com",
    },
    "EMP004": {
        "name": "Vikram Nair",
        "department": "Compliance",
        "role": "Compliance Officer",
        "level": "L5",
        "manager": "EMP013",
        "tenure_years": 9,
        "performance_rating": 4.0,
        "salary": 3_000_000,
        "location": "Mumbai",
        "status": "Active",
        "role_type": "operations",
        "email": "vikram.nair@cymbalwealth.com",
    },
    "EMP005": {
        "name": "Deepika Menon",
        "department": "HR",
        "role": "HR Business Partner",
        "level": "L5",
        "manager": "EMP014",
        "tenure_years": 4,
        "performance_rating": 4.3,
        "salary": 2_100_000,
        "location": "Hyderabad",
        "status": "Active",
        "role_type": "operations",
        "email": "deepika.menon@cymbalwealth.com",
    },
    "EMP006": {
        "name": "Arjun Patel",
        "department": "Engineering",
        "role": "Data Scientist",
        "level": "L4",
        "manager": "EMP010",
        "tenure_years": 2,
        "performance_rating": 3.9,
        "salary": 1_600_000,
        "location": "Pune",
        "status": "Active",
        "role_type": "technology",
        "email": "arjun.patel@cymbalwealth.com",
    },
    "EMP007": {
        "name": "Sunita Krishnan",
        "department": "Finance",
        "role": "CFO",
        "level": "L8",
        "manager": "EMP015",
        "tenure_years": 12,
        "performance_rating": 4.7,
        "salary": 8_000_000,
        "location": "Mumbai",
        "status": "Active",
        "role_type": "leadership",
        "email": "sunita.krishnan@cymbalwealth.com",
    },
    "EMP008": {
        "name": "Rohan Gupta",
        "department": "Operations",
        "role": "Operations Manager",
        "level": "L6",
        "manager": "EMP013",
        "tenure_years": 6,
        "performance_rating": 3.7,
        "salary": 2_800_000,
        "location": "Chennai",
        "status": "Active",
        "role_type": "operations",
        "email": "rohan.gupta@cymbalwealth.com",
    },
    "EMP009": {
        "name": "Kavitha Reddy",
        "department": "Product",
        "role": "Product Manager",
        "level": "L5",
        "manager": "EMP016",
        "tenure_years": 3,
        "performance_rating": 4.1,
        "salary": 2_400_000,
        "location": "Bangalore",
        "status": "Active",
        "role_type": "technology",
        "email": "kavitha.reddy@cymbalwealth.com",
    },
    "EMP010": {
        "name": "Suresh Chandran",
        "department": "Engineering",
        "role": "Engineering Director",
        "level": "L7",
        "manager": "EMP015",
        "tenure_years": 8,
        "performance_rating": 4.6,
        "salary": 5_500_000,
        "location": "Bangalore",
        "status": "Active",
        "role_type": "leadership",
        "email": "suresh.chandran@cymbalwealth.com",
    },
    "EMP011": {
        "name": "Meera Agarwal",
        "department": "Risk",
        "role": "Chief Risk Officer",
        "level": "L8",
        "manager": "EMP015",
        "tenure_years": 15,
        "performance_rating": 4.8,
        "salary": 9_000_000,
        "location": "Mumbai",
        "status": "Active",
        "role_type": "leadership",
        "email": "meera.agarwal@cymbalwealth.com",
    },
}


def get_employee(employee_id: str) -> dict:
    """Fetch an employee record from HRIS.

    Args:
        employee_id: Employee identifier (e.g. "EMP001").

    Returns:
        Employee record dict, or an error dict if not found.
    """
    record = DEMO_EMPLOYEES.get(employee_id.upper())
    if record is None:
        return {"error": f"Employee '{employee_id}' not found", "employee_id": employee_id}
    return {"employee_id": employee_id, **record}


def get_direct_reports(manager_id: str) -> list[dict]:
    """Fetch the direct reports for a manager.

    Args:
        manager_id: Manager's employee ID.

    Returns:
        List of employee records for direct reports.
    """
    reports = [
        {"employee_id": eid, **emp}
        for eid, emp in DEMO_EMPLOYEES.items()
        if emp.get("manager") == manager_id.upper()
    ]
    return reports


def get_org_chart(department: str) -> dict:
    """Fetch an org chart summary for a department.

    Args:
        department: Department name (case-insensitive).

    Returns:
        Dict with department summary and employee list.
    """
    members = [
        {"employee_id": eid, **emp}
        for eid, emp in DEMO_EMPLOYEES.items()
        if emp.get("department", "").lower() == department.lower()
    ]
    if not members:
        return {"error": f"No employees found in department '{department}'"}
    return {
        "department": department,
        "headcount": len(members),
        "employees": members,
    }


def get_open_positions(department: str | None = None) -> list[dict]:
    """Return stub open positions (demo data).

    Args:
        department: Optional department filter.

    Returns:
        List of open requisition dicts.
    """
    positions = [
        {
            "job_id": "JOB-2025-001",
            "title": "Senior Software Engineer",
            "department": "Engineering",
            "experience_required": 5,
            "status": "Open",
        },
        {
            "job_id": "JOB-2025-002",
            "title": "Risk Analyst",
            "department": "Risk",
            "experience_required": 3,
            "status": "Open",
        },
        {
            "job_id": "JOB-2025-003",
            "title": "Relationship Manager",
            "department": "Wealth Management",
            "experience_required": 4,
            "status": "Open",
        },
    ]
    if department:
        positions = [p for p in positions if p["department"].lower() == department.lower()]
    return positions
