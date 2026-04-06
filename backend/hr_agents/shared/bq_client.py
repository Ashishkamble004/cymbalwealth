"""BigQuery client for the HR analytics dataset.

Dataset: general-ak.hr_analytics
Tables (12): employees, departments, performance_reviews, payroll, attendance,
             leave_requests, job_postings, candidates, interviews,
             training_programs, employee_training, onboarding_tasks
"""

from __future__ import annotations

PROJECT = "general-ak"
DATASET = "hr_analytics"

# HR dataset schema reference for NL→SQL agents
HR_SCHEMA = f"""
Dataset: {PROJECT}.{DATASET}

Table: employees
  employee_id STRING, name STRING, department STRING, hire_date DATE,
  salary FLOAT64, performance_rating FLOAT64, manager_id STRING,
  status STRING, location STRING, level STRING

Table: departments
  dept_id STRING, dept_name STRING, head_count INT64,
  budget FLOAT64, head_employee_id STRING

Table: performance_reviews
  review_id STRING, employee_id STRING, period STRING, rating FLOAT64,
  feedback STRING, reviewer_id STRING, review_date DATE

Table: payroll
  payroll_id STRING, employee_id STRING, base_salary FLOAT64, bonus FLOAT64,
  tax_deductions FLOAT64, net_pay FLOAT64, pay_date DATE

Table: attendance
  record_id STRING, employee_id STRING, date DATE, check_in TIME,
  check_out TIME, hours_worked FLOAT64

Table: leave_requests
  request_id STRING, employee_id STRING, leave_type STRING,
  start_date DATE, end_date DATE, status STRING, reason STRING

Table: job_postings
  posting_id STRING, title STRING, department STRING,
  experience_required INT64, skills_required STRING, status STRING

Table: candidates
  candidate_id STRING, name STRING, email STRING, resume_text STRING,
  skills STRING, experience_years INT64, applied_posting STRING

Table: interviews
  interview_id STRING, candidate_id STRING, interviewer_id STRING,
  date DATE, feedback STRING, recommendation STRING

Table: training_programs
  program_id STRING, title STRING, duration_days INT64,
  skills_taught STRING, capacity INT64

Table: employee_training
  record_id STRING, employee_id STRING, program_id STRING,
  completion_date DATE, score FLOAT64

Table: onboarding_tasks
  task_id STRING, employee_id STRING, task_name STRING,
  assigned_to STRING, due_date DATE, status STRING
"""

_DML_KEYWORDS = ("INSERT", "UPDATE", "DELETE", "DROP", "CREATE", "TRUNCATE", "MERGE")

_client = None


def _get_client():
    """Return a cached BigQuery client."""
    global _client
    if _client is None:
        from google.cloud import bigquery
        _client = bigquery.Client(project=PROJECT)
    return _client


def run_query(sql: str) -> list[dict]:
    """Execute a read-only SQL query against the HR analytics dataset.

    Args:
        sql: SELECT query to execute. DML statements are rejected.

    Returns:
        List of row dicts.

    Raises:
        ValueError: If the query contains DML keywords.
        google.cloud.exceptions.GoogleCloudError: On BigQuery errors.
    """
    upper = sql.upper()
    for kw in _DML_KEYWORDS:
        if kw in upper:
            raise ValueError(
                f"Only SELECT queries are permitted. Found keyword: {kw}"
            )

    client = _get_client()
    rows = client.query(sql).result()
    return [dict(row) for row in rows]
