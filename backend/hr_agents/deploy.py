"""Deploy all 6 HR agents to Vertex AI Agent Engine.

Usage:
    cd backend
    python -m hr_agents.deploy              # deploy all (creates new)
    python -m hr_agents.deploy --update     # update existing agents
    python -m hr_agents.deploy --agent policy_qa  # deploy one agent

Each agent is wrapped in an AdkApp and deployed as a ReasoningEngine
with SPIFFE agent identity and Agent Gateway routing.
"""

import argparse
import json
import sys

import vertexai
from vertexai.preview import reasoning_engines

PROJECT = "general-ak"
LOCATION = "us-central1"
STAGING_BUCKET = "gs://cymbal-wealth-staging"

AGENT_GATEWAY = f"projects/{PROJECT}/locations/{LOCATION}/agentGateways/agent-gateway"
NETWORK_ATTACHMENT = f"projects/{PROJECT}/regions/{LOCATION}/networkAttachments/agent-gateway-na"

REQUIREMENTS = [
    "google-adk[a2a,agent-identity]>=1.27.4",
    "google-cloud-bigquery",
    "google-cloud-secret-manager",
    "google-cloud-aiplatform[adk,agent_engines]",
    "vertexai",
    "requests",
    "google-auth>=2.0",
]

EXTRA_PACKAGES = ["./hr_agents"]

AGENT_PLATFORM_CONFIG = {
    "identity_type": "AGENT_IDENTITY",
    "agent_gateway_config": {
        "agent_to_anywhere_config": {
            "agent_gateway": AGENT_GATEWAY,
        }
    },
}

CONFIG_PATH = "hr_agents/.agent_engine_config.json"


def _load_existing_config() -> dict:
    try:
        with open(CONFIG_PATH) as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy HR agents to Agent Engine")
    parser.add_argument("--update", action="store_true", help="Update existing agents instead of creating new ones")
    parser.add_argument("--agent", type=str, help="Deploy a single agent by key (e.g. policy_qa)")
    args = parser.parse_args()

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING_BUCKET)
    client = vertexai.Client(project=PROJECT, location=LOCATION, http_options=dict(api_version="v1beta1"))

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

    if args.agent:
        agents = [(k, d, f) for k, d, f in agents if k == args.agent]
        if not agents:
            print(f"Unknown agent: {args.agent}")
            sys.exit(1)

    existing_config = _load_existing_config()
    config: dict[str, str] = dict(existing_config)

    for key, display_name, factory in agents:
        print(f"{'Updating' if args.update else 'Deploying'} {display_name}...")
        try:
            app = reasoning_engines.AdkApp(agent=factory(), enable_tracing=True)
            deploy_config = dict(
                staging_bucket=STAGING_BUCKET,
                requirements=REQUIREMENTS,
                extra_packages=EXTRA_PACKAGES,
                display_name=f"cymbal-wealth-{key}",
                env_vars={
                    "GOOGLE_GENAI_USE_VERTEXAI": "True",
                    "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
                },
                **AGENT_PLATFORM_CONFIG,
            )

            if args.update and key in existing_config and not existing_config[key].startswith("FAILED"):
                engine = client.agent_engines.update(
                    name=existing_config[key], agent=app, config=deploy_config,
                )
            else:
                engine = client.agent_engines.create(agent=app, config=deploy_config)

            config[key] = engine.api_resource.name
            print(f"  OK  {engine.api_resource.name}")
        except Exception as exc:
            config[key] = existing_config.get(key, f"FAILED: {exc}")
            print(f"  FAIL  {exc}")

    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

    ok = sum(1 for v in config.values() if not v.startswith("FAILED"))
    print(f"\nConfig saved to {CONFIG_PATH}. {ok}/{len(config)} agents deployed.")


if __name__ == "__main__":
    main()
