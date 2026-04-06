#!/usr/bin/env python3
"""
Set up HR agent infrastructure:
- Upload policy documents to GCS
- Create BigQuery hr_analytics dataset and tables
"""
from pathlib import Path

PROJECT = "general-ak"
LOCATION = "us-central1"
GCS_BUCKET = "cymbal-wealth"
BQ_DATASET = "hr_analytics"
DOCS_GCS_PREFIX = "hr-documents/"


def _build_schema():
    from google.cloud import bigquery
    F = bigquery.SchemaField
    return {
        "employees": [
            F("employee_id", "STRING", mode="REQUIRED"),
            F("name", "STRING"),
            F("email", "STRING"),
            F("department", "STRING"),
            F("hire_date", "DATE"),
            F("salary", "FLOAT64"),
            F("performance_rating", "FLOAT64"),
            F("manager_id", "STRING"),
            F("status", "STRING"),
            F("location", "STRING"),
            F("level", "STRING"),
            F("band", "INTEGER"),
        ],
        "departments": [
            F("dept_id", "STRING", mode="REQUIRED"),
            F("dept_name", "STRING"),
            F("head_count", "INTEGER"),
            F("budget", "FLOAT64"),
            F("head_employee_id", "STRING"),
            F("cost_center", "STRING"),
        ],
        "performance_reviews": [
            F("review_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("period", "STRING"),
            F("rating", "FLOAT64"),
            F("feedback", "STRING"),
            F("reviewer_id", "STRING"),
            F("review_date", "DATE"),
            F("goals_met_pct", "FLOAT64"),
        ],
        "payroll": [
            F("payroll_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("pay_period", "STRING"),
            F("base_salary", "FLOAT64"),
            F("variable_pay", "FLOAT64"),
            F("bonus", "FLOAT64"),
            F("tax_deductions", "FLOAT64"),
            F("pf_deduction", "FLOAT64"),
            F("net_pay", "FLOAT64"),
            F("pay_date", "DATE"),
        ],
        "attendance": [
            F("record_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("date", "DATE"),
            F("check_in", "TIME"),
            F("check_out", "TIME"),
            F("hours_worked", "FLOAT64"),
            F("work_mode", "STRING"),
        ],
        "leave_requests": [
            F("request_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("leave_type", "STRING"),
            F("start_date", "DATE"),
            F("end_date", "DATE"),
            F("days_count", "FLOAT64"),
            F("status", "STRING"),
            F("reason", "STRING"),
            F("approved_by", "STRING"),
        ],
        "job_postings": [
            F("posting_id", "STRING", mode="REQUIRED"),
            F("title", "STRING"),
            F("department", "STRING"),
            F("experience_required_years", "INTEGER"),
            F("skills_required", "STRING"),
            F("band", "INTEGER"),
            F("status", "STRING"),
            F("posted_date", "DATE"),
            F("target_close_date", "DATE"),
        ],
        "candidates": [
            F("candidate_id", "STRING", mode="REQUIRED"),
            F("name", "STRING"),
            F("email", "STRING"),
            F("phone", "STRING"),
            F("resume_text", "STRING"),
            F("skills", "STRING"),
            F("experience_years", "INTEGER"),
            F("applied_posting_id", "STRING"),
            F("current_ctc", "FLOAT64"),
            F("expected_ctc", "FLOAT64"),
            F("ai_score", "FLOAT64"),
            F("status", "STRING"),
        ],
        "interviews": [
            F("interview_id", "STRING", mode="REQUIRED"),
            F("candidate_id", "STRING"),
            F("interviewer_id", "STRING"),
            F("interview_type", "STRING"),
            F("interview_date", "DATETIME"),
            F("feedback", "STRING"),
            F("recommendation", "STRING"),
            F("rating", "FLOAT64"),
        ],
        "training_programs": [
            F("program_id", "STRING", mode="REQUIRED"),
            F("title", "STRING"),
            F("category", "STRING"),
            F("duration_days", "INTEGER"),
            F("skills_taught", "STRING"),
            F("capacity", "INTEGER"),
            F("mode", "STRING"),
            F("mandatory", "BOOL"),
        ],
        "employee_training": [
            F("record_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("program_id", "STRING"),
            F("enrollment_date", "DATE"),
            F("completion_date", "DATE"),
            F("score", "FLOAT64"),
            F("certificate_issued", "BOOL"),
        ],
        "onboarding_tasks": [
            F("task_id", "STRING", mode="REQUIRED"),
            F("employee_id", "STRING"),
            F("task_name", "STRING"),
            F("task_category", "STRING"),
            F("assigned_to", "STRING"),
            F("due_date", "DATE"),
            F("completed_date", "DATE"),
            F("status", "STRING"),
            F("notes", "STRING"),
        ],
    }


# Table names exported for inspection without requiring google-cloud installed.
TABLES = {
    "employees", "departments", "performance_reviews", "payroll",
    "attendance", "leave_requests", "job_postings", "candidates",
    "interviews", "training_programs", "employee_training", "onboarding_tasks",
}


def upload_documents():
    from google.cloud import storage
    client = storage.Client(project=PROJECT)
    bucket = client.bucket(GCS_BUCKET)
    docs_dir = Path(__file__).parent / "documents"
    uploaded = []
    for doc_file in sorted(docs_dir.glob("*.md")):
        blob_name = DOCS_GCS_PREFIX + doc_file.name
        blob = bucket.blob(blob_name)
        blob.upload_from_filename(str(doc_file), content_type="text/markdown")
        uri = f"gs://{GCS_BUCKET}/{blob_name}"
        uploaded.append(uri)
        print(f"  ✓ {uri}")
    return uploaded


def create_bq_dataset(client):
    from google.cloud import bigquery
    dataset_ref = f"{PROJECT}.{BQ_DATASET}"
    try:
        client.get_dataset(dataset_ref)
        print(f"  Dataset {BQ_DATASET} already exists")
        return False
    except Exception:
        ds = bigquery.Dataset(dataset_ref)
        ds.location = LOCATION
        ds.description = "Cymbal Wealth HR Analytics Data Lake"
        client.create_dataset(ds)
        print(f"  ✓ Created dataset: {BQ_DATASET}")
        return True


def create_bq_tables(client):
    from google.cloud import bigquery
    tables_schema = _build_schema()
    created = []
    for table_name, schema in tables_schema.items():
        table_id = f"{PROJECT}.{BQ_DATASET}.{table_name}"
        try:
            client.get_table(table_id)
            print(f"  Table {table_name} already exists")
        except Exception:
            table = bigquery.Table(table_id, schema=schema)
            client.create_table(table)
            created.append(table_name)
            print(f"  ✓ Created: {table_name}")
    return created


if __name__ == "__main__":
    from google.cloud import bigquery

    print("=" * 60)
    print("Cymbal Wealth HR Agent Infrastructure Setup")
    print("=" * 60)

    print("\n[1/3] Uploading HR policy documents to GCS...")
    try:
        uploaded = upload_documents()
        print(f"  Uploaded {len(uploaded)} documents")
    except Exception as e:
        print(f"  ERROR: {e}")

    bq_client = bigquery.Client(project=PROJECT)

    print("\n[2/3] Creating BigQuery dataset...")
    try:
        create_bq_dataset(bq_client)
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\n[3/3] Creating BigQuery tables...")
    try:
        created = create_bq_tables(bq_client)
        print(f"  Created {len(created)} new tables")
    except Exception as e:
        print(f"  ERROR: {e}")

    print("\nDone!")
