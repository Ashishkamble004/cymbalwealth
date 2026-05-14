#!/usr/bin/env python3
"""
Redshift Serverless Setup Script for CymbalWealth

One-time script to create tables and seed demo data into Redshift Serverless
after the SAM stack (cymbal-wealth-a2a) has been deployed.

Usage:
    # After SAM deploy, get outputs:
    export REDSHIFT_SECRET_ARN=$(aws cloudformation describe-stacks \
        --stack-name cymbal-wealth-a2a \
        --query 'Stacks[0].Outputs[?OutputKey==`RedshiftSecretArn`].OutputValue' \
        --output text)

    python setup_redshift.py
"""

import os
import sys
import time
from pathlib import Path

import boto3


# ---------------------------------------------------------------------------
# Configuration from environment
# ---------------------------------------------------------------------------
REDSHIFT_WORKGROUP = os.environ.get("REDSHIFT_WORKGROUP", "cymbal-wealth-wg")
REDSHIFT_DATABASE = os.environ.get("REDSHIFT_DATABASE", "cymbalwealth")
REDSHIFT_SECRET_ARN = os.environ.get("REDSHIFT_SECRET_ARN")
AWS_REGION = os.environ.get("AWS_REGION", "us-east-1")


def _get_client():
    """Return a boto3 redshift-data client for the configured region."""
    return boto3.client("redshift-data", region_name=AWS_REGION)


# ---------------------------------------------------------------------------
# Core helpers
# ---------------------------------------------------------------------------
def run_sql(sql: str, description: str) -> bool:
    """Execute a single SQL statement via Redshift Data API and poll until done.

    Uses WorkgroupName (Redshift Serverless) rather than ClusterIdentifier.

    Returns True on success, False on failure.
    """
    client = _get_client()

    print(f"  Running: {description} ... ", end="", flush=True)

    response = client.execute_statement(
        WorkgroupName=REDSHIFT_WORKGROUP,
        Database=REDSHIFT_DATABASE,
        SecretArn=REDSHIFT_SECRET_ARN,
        Sql=sql,
    )
    statement_id = response["Id"]

    # Poll until terminal state
    while True:
        status_resp = client.describe_statement(Id=statement_id)
        status = status_resp["Status"]

        if status == "FINISHED":
            print("✓")
            return True
        elif status in ("FAILED", "ABORTED"):
            error = status_resp.get("Error", "Unknown error")
            print(f"✗  ({status}: {error})")
            return False

        time.sleep(1)


def run_sql_file(filepath: str) -> None:
    """Read a .sql file, split on semicolons, and execute each statement."""
    path = Path(filepath)
    if not path.exists():
        print(f"  ERROR: SQL file not found: {filepath}")
        sys.exit(1)

    contents = path.read_text()
    statements = [s.strip() for s in contents.split(";") if s.strip()]

    print(f"\n--- Executing {path.name} ({len(statements)} statement(s)) ---")
    for i, stmt in enumerate(statements, 1):
        # Use first line (or first 60 chars) as the description
        first_line = stmt.split("\n")[0].strip()
        desc = f"[{i}/{len(statements)}] {first_line[:60]}"
        ok = run_sql(stmt, desc)
        if not ok:
            print(f"  WARNING: Statement {i} failed — continuing with remaining statements")


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------
def main() -> None:
    # Validate required config
    if not REDSHIFT_SECRET_ARN:
        print("ERROR: REDSHIFT_SECRET_ARN environment variable is required.\n")
        print("After deploying the SAM stack, retrieve it with:\n")
        print("  export REDSHIFT_SECRET_ARN=$(aws cloudformation describe-stacks \\")
        print("      --stack-name cymbal-wealth-a2a \\")
        print("      --query 'Stacks[0].Outputs[?OutputKey==`RedshiftSecretArn`].OutputValue' \\")
        print("      --output text)\n")
        sys.exit(1)

    # Print config summary
    print("=" * 60)
    print("CymbalWealth Redshift Serverless Setup")
    print("=" * 60)
    print(f"  Workgroup : {REDSHIFT_WORKGROUP}")
    print(f"  Database  : {REDSHIFT_DATABASE}")
    print(f"  Secret ARN: {REDSHIFT_SECRET_ARN}")
    print(f"  Region    : {AWS_REGION}")
    print("=" * 60)

    # Resolve SQL file paths relative to this script's directory
    script_dir = Path(__file__).resolve().parent
    credit_sql = script_dir / "credit_data.sql"
    regulatory_sql = script_dir / "regulatory_data.sql"

    # Execute schema + seed SQL
    run_sql_file(str(credit_sql))
    run_sql_file(str(regulatory_sql))

    # Quick verification
    print("\n--- Verification: credit_profiles ---")
    client = _get_client()
    response = client.execute_statement(
        WorkgroupName=REDSHIFT_WORKGROUP,
        Database=REDSHIFT_DATABASE,
        SecretArn=REDSHIFT_SECRET_ARN,
        Sql="SELECT customer_ref, cibil_score, credit_grade FROM credit_profiles ORDER BY customer_ref",
    )
    statement_id = response["Id"]

    # Poll for completion
    while True:
        status_resp = client.describe_statement(Id=statement_id)
        status = status_resp["Status"]
        if status == "FINISHED":
            break
        elif status in ("FAILED", "ABORTED"):
            error = status_resp.get("Error", "Unknown error")
            print(f"  Verification query failed: {error}")
            sys.exit(1)
        time.sleep(1)

    # Fetch and display results
    result = client.get_statement_result(Id=statement_id)
    rows = result.get("Records", [])

    if not rows:
        print("  No rows found in credit_profiles (seed data may not have loaded)")
    else:
        print(f"  {'Customer Ref':<20} {'CIBIL Score':<15} {'Credit Grade'}")
        print(f"  {'-'*20} {'-'*15} {'-'*15}")
        for row in rows:
            customer_ref = row[0].get("stringValue", "N/A")
            cibil_score = row[1].get("longValue", row[1].get("stringValue", "N/A"))
            credit_grade = row[2].get("stringValue", "N/A")
            print(f"  {customer_ref:<20} {str(cibil_score):<15} {credit_grade}")

    print("\n✓ Setup complete!")


if __name__ == "__main__":
    main()
