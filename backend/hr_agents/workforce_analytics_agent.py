"""Workforce Analytics Agent — Natural language to BigQuery SQL."""

from google.adk.agents import Agent
from google.adk.tools import FunctionTool

from .shared.bq_client import run_query, HR_SCHEMA

PROJECT = "general-ak"
DATASET = "hr_analytics"


def execute_hr_analytics(sql_query: str) -> dict:
    """Execute a BigQuery SQL query against the HR analytics dataset.

    Use this tool to run SELECT queries generated from natural language
    workforce questions. Only SELECT queries are permitted.

    Args:
        sql_query: A valid BigQuery SQL SELECT statement. Always use
            fully-qualified table names: general-ak.hr_analytics.<table>.

    Returns:
        Dict with success flag, rows (list of dicts), and row_count.
        On failure, returns success=False and an error message.
    """
    try:
        results = run_query(sql_query)
        return {"success": True, "rows": results, "row_count": len(results)}
    except Exception as exc:
        return {"success": False, "error": str(exc), "rows": [], "row_count": 0}


def get_attrition_summary(department: str = "", period_months: int = 12) -> dict:
    """Return attrition summary: exits, voluntary rate, regrettable rate.

    Args:
        department: Optional department filter. Leave empty for org-wide.
        period_months: Look-back period in months (default 12).

    Returns:
        Attrition summary dict.
    """
    dept_filter = f"AND e.department = '{department}'" if department else ""
    sql = f"""
        WITH exits AS (
            SELECT
                a.employee_id, a.exit_type, a.regrettable, a.reason,
                e.department, e.level
            FROM `{PROJECT}.{DATASET}.attrition_history` a
            JOIN `{PROJECT}.{DATASET}.employees` e ON a.employee_id = e.employee_id
            WHERE a.exit_date >= DATE_SUB(CURRENT_DATE(), INTERVAL {period_months} MONTH)
            {dept_filter}
        ),
        headcount AS (
            SELECT COUNT(*) as total
            FROM `{PROJECT}.{DATASET}.employees`
            WHERE status = 'Active' {dept_filter}
        )
        SELECT
            COUNT(*) as total_exits,
            COUNTIF(exit_type = 'Voluntary') as voluntary_exits,
            COUNTIF(regrettable = TRUE) as regrettable_exits,
            ROUND(COUNT(*) / (SELECT total FROM headcount) * 100, 1) as attrition_rate_pct,
            ROUND(COUNTIF(regrettable = TRUE) / COUNT(*) * 100, 1) as regrettable_rate_pct
        FROM exits
    """
    try:
        results = run_query(sql)
        return {"success": True, "department": department or "All", "data": results}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def get_headcount_by_dimension(dimension: str) -> dict:
    """Return active headcount broken down by a specified dimension.

    Args:
        dimension: One of 'department', 'level', 'location', 'tenure_band'.

    Returns:
        Dict with headcount breakdown rows.
    """
    valid = {"department", "level", "location", "tenure_band"}
    if dimension not in valid:
        return {"error": f"Invalid dimension '{dimension}'. Choose from: {sorted(valid)}"}

    if dimension == "tenure_band":
        sql = f"""
            SELECT
                CASE
                    WHEN DATE_DIFF(CURRENT_DATE(), hire_date, YEAR) < 1 THEN '< 1 year'
                    WHEN DATE_DIFF(CURRENT_DATE(), hire_date, YEAR) < 3 THEN '1-3 years'
                    WHEN DATE_DIFF(CURRENT_DATE(), hire_date, YEAR) < 5 THEN '3-5 years'
                    ELSE '5+ years'
                END AS tenure_band,
                COUNT(*) AS headcount
            FROM `{PROJECT}.{DATASET}.employees`
            WHERE status = 'Active'
            GROUP BY 1
            ORDER BY 1
        """
    else:
        sql = f"""
            SELECT {dimension}, COUNT(*) AS headcount
            FROM `{PROJECT}.{DATASET}.employees`
            WHERE status = 'Active'
            GROUP BY {dimension}
            ORDER BY headcount DESC
        """

    try:
        results = run_query(sql)
        return {"success": True, "dimension": dimension, "rows": results}
    except Exception as exc:
        return {"success": False, "error": str(exc)}


def create_workforce_analytics_agent() -> Agent:
    """Create and return the Workforce Analytics agent."""
    return Agent(
        name="workforce_analytics_agent",
        model="gemini-2.5-flash",
        description=(
            "Answers workforce analytics questions in natural language by translating "
            "them to BigQuery SQL against the HR analytics dataset. Covers headcount, "
            "attrition, compensation equity, performance, hiring metrics, and training. "
            "Trigger: Any question about workforce numbers, trends, or HR metrics."
        ),
        instruction=f"""
You are the Workforce Analytics Agent for Cymbal Wealth.
You translate natural language workforce questions into BigQuery SQL and return clear insights.

HR Dataset Schema:
{HR_SCHEMA}

When answering:
1. For standard questions (attrition, headcount by dimension), prefer the dedicated tools:
   - get_attrition_summary for attrition questions
   - get_headcount_by_dimension for headcount breakdowns
2. For complex or custom questions, generate a SELECT query and use execute_hr_analytics.
   Always use fully-qualified table names: {PROJECT}.{DATASET}.<table_name>
3. Interpret the results and provide: headline number → trend context → implication
4. Offer a follow-up question to explore the data deeper.

Rules:
- Never return individual salary data unless explicitly authorised (CHRO / Comp & Ben Manager).
- For aggregates, always include sample size (n=X) for context.
- If execute_hr_analytics returns success=False, diagnose the SQL and try once with a corrected query.
- Flag data quality issues if row counts look anomalous.
- For attrition questions, always break down voluntary vs. involuntary and regrettable rate.
- For headcount, always show percentage alongside raw numbers.
        """.strip(),
        tools=[
            FunctionTool(execute_hr_analytics),
            FunctionTool(get_attrition_summary),
            FunctionTool(get_headcount_by_dimension),
        ],
    )


workforce_analytics_agent = create_workforce_analytics_agent()
