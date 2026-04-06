"""Deploy all 6 HR agents to Vertex AI Agent Engine.

Usage:
    cd backend
    python -m hr_agents.deploy

Each agent is wrapped in an AdkApp and deployed as a ReasoningEngine.
Resource names are saved to hr_agents/.agent_engine_config.json.
"""

import json
import sys

import vertexai
from vertexai.preview import reasoning_engines

PROJECT = "general-ak"
LOCATION = "us-central1"
GCS_BUCKET = "cymbal-wealth"

REQUIREMENTS = [
    "google-adk>=1.27.4",
    "google-cloud-bigquery",
    "google-cloud-secret-manager",
    "google-cloud-aiplatform",
    "numpy",
    "vertexai",
    "requests",
]


def main() -> None:
    vertexai.init(project=PROJECT, location=LOCATION)

    sys.path.insert(0, ".")
    from hr_agents.policy_qa_agent import create_policy_qa_agent
    from hr_agents.meeting_prep_agent import create_meeting_prep_agent
    from hr_agents.resume_screening_agent import create_resume_screening_agent
    from hr_agents.onboarding_agent import create_onboarding_agent
    from hr_agents.talent_acquisition_orchestrator import create_talent_acquisition_orchestrator
    from hr_agents.workforce_analytics_agent import create_workforce_analytics_agent

    agents = [
        ("policy_qa", "HR Policy Q&A Assistant", create_policy_qa_agent),
        ("meeting_prep", "1:1 Meeting Prep Assistant", create_meeting_prep_agent),
        ("resume_screening", "Resume Screening Agent", create_resume_screening_agent),
        ("onboarding", "Onboarding Orchestration Agent", create_onboarding_agent),
        ("talent_acquisition", "Talent Acquisition Orchestrator", create_talent_acquisition_orchestrator),
        ("workforce_analytics", "Workforce Analytics Agent", create_workforce_analytics_agent),
    ]

    config: dict[str, str] = {}
    for key, display_name, factory in agents:
        print(f"Deploying {display_name}...")
        try:
            app = reasoning_engines.AdkApp(agent=factory(), enable_tracing=True)
            remote = reasoning_engines.ReasoningEngine.create(
                app,
                requirements=REQUIREMENTS,
                display_name=f"cymbal-wealth-{key}",
                gcs_dir_name=f"gs://{GCS_BUCKET}/agent-engine/{key}",
            )
            config[key] = remote.resource_name
            print(f"  OK  {remote.resource_name}")
        except Exception as exc:
            config[key] = f"FAILED: {exc}"
            print(f"  FAIL  {exc}")

    config_path = "hr_agents/.agent_engine_config.json"
    with open(config_path, "w") as f:
        json.dump(config, f, indent=2)

    ok = sum(1 for v in config.values() if not v.startswith("FAILED"))
    print(f"\nConfig saved to {config_path}. {ok}/{len(config)} agents deployed.")


if __name__ == "__main__":
    main()
