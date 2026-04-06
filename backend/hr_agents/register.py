"""Register deployed HR agents with Gemini Enterprise (Discovery Engine).

Usage:
    cd backend
    python -m hr_agents.register

Reads resource names from hr_agents/.agent_engine_config.json (produced by deploy.py).
Saves registration IDs to hr_agents/.agent_registration_config.json.
"""

import json
import os
import subprocess

import requests

PROJECT_ID = os.environ.get("GCP_PROJECT_ID", "general-ak")
APP_ID = os.environ.get("GEMINI_ENTERPRISE_APP_ID", "")
ENDPOINT = "https://global-discoveryengine.googleapis.com/v1alpha"

AGENT_DESCRIPTIONS = {
    "policy_qa": (
        "Answers employee questions about HR policies, leave entitlements, benefits, "
        "and workplace guidelines using the Cymbal Wealth policy knowledge base. "
        "Use when employees ask: 'What is the policy on...', "
        "'How many leave days do I have', 'Am I eligible for...'"
    ),
    "meeting_prep": (
        "Prepares personalised 1:1 meeting agendas for managers using OKR progress, "
        "feedback themes, and retention signals. "
        "Use when asked: 'Prepare my 1:1 with [name]' or 'What should I discuss with [name]?'"
    ),
    "resume_screening": (
        "Screens and shortlists job applicants, scores candidate fit using semantic AI, "
        "checks diversity metrics, and writes ATS notes. "
        "Use for: 'Screen candidates for job [ID]', 'Who should I shortlist for [role]?'"
    ),
    "onboarding": (
        "Manages new hire onboarding: checklists, IT provisioning, welcome communications, "
        "and progress tracking. "
        "Use for: 'Onboard employee [ID]', 'What is the status of [name]'s onboarding?'"
    ),
    "talent_acquisition": (
        "Manages the full hiring lifecycle: requisition validation, job posting, "
        "candidate screening, interview scheduling, and pipeline analytics. "
        "Use for: 'Manage hiring for job [ID]', 'What is our pipeline status for [role]?'"
    ),
    "workforce_analytics": (
        "Answers workforce analytics questions using the HR data lake in BigQuery. "
        "Covers headcount, attrition, compensation equity, performance, hiring metrics, "
        "and training compliance. "
        "Use for any question about workforce numbers, trends, or HR metrics."
    ),
}

DISPLAY_NAMES = {
    "policy_qa": "HR Policy Q&A Assistant",
    "meeting_prep": "1:1 Meeting Prep Assistant",
    "resume_screening": "Resume Screening Agent",
    "onboarding": "Onboarding Orchestration Agent",
    "talent_acquisition": "Talent Acquisition Orchestrator",
    "workforce_analytics": "Workforce Analytics Agent",
}


def _access_token() -> str:
    result = subprocess.run(
        ["gcloud", "auth", "print-access-token"],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout.strip()


def register_agent(key: str, resource_name: str, assistant_url: str, token: str) -> str:
    """Register a single agent with Gemini Enterprise.

    Args:
        key: Agent key (e.g. "policy_qa").
        resource_name: Full Vertex AI resource name.
        assistant_url: Full Discovery Engine assistant URL.
        token: Bearer token (fetched once by the caller).

    Returns:
        Registered agent ID.
    """
    payload = {
        "displayName": DISPLAY_NAMES[key],
        "description": AGENT_DESCRIPTIONS[key],
        "adkAgentDefinition": {
            "provisionedReasoningEngine": {
                "reasoningEngine": resource_name,
            }
        },
    }
    response = requests.post(
        f"{assistant_url}/agents",
        headers={
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
            "X-Goog-User-Project": PROJECT_ID,
        },
        json=payload,
        timeout=30,
    )
    response.raise_for_status()
    agent_id = response.json().get("name", "").split("/")[-1]
    return agent_id


def main() -> None:
    if not APP_ID:
        print("ERROR: Set GEMINI_ENTERPRISE_APP_ID environment variable.")
        return

    collection = f"projects/{PROJECT_ID}/locations/global/collections/default_collection"
    assistant_url = f"{ENDPOINT}/{collection}/engines/{APP_ID}/assistants/default_assistant"
    token = _access_token()

    config_path = "hr_agents/.agent_engine_config.json"
    with open(config_path) as f:
        deployed: dict[str, str] = json.load(f)

    registered: dict[str, str] = {}
    for key, resource_name in deployed.items():
        if resource_name.startswith("FAILED"):
            print(f"  SKIP  {key} (deployment failed)")
            continue
        print(f"Registering {DISPLAY_NAMES.get(key, key)}...")
        try:
            agent_id = register_agent(key, resource_name, assistant_url, token)
            registered[key] = agent_id
            print(f"  OK  Agent ID: {agent_id}")
        except Exception as exc:
            registered[key] = f"FAILED: {exc}"
            print(f"  FAIL  {exc}")

    out_path = "hr_agents/.agent_registration_config.json"
    with open(out_path, "w") as f:
        json.dump(registered, f, indent=2)

    ok = sum(1 for v in registered.values() if not v.startswith("FAILED"))
    print(f"\nRegistration complete. {ok}/{len(registered)} agents registered.")
    print(f"View at: https://console.cloud.google.com/gen-app-builder/engines/{APP_ID}")


if __name__ == "__main__":
    main()
