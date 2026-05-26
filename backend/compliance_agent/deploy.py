"""Deploy Compliance & Reporting agent to Vertex AI Agent Engine.

Usage:
    cd backend
    python -m compliance_agent.deploy            # create new
    python -m compliance_agent.deploy --update   # update existing
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
    "google-cloud-aiplatform[adk,agent_engines]",
    "vertexai",
    "requests",
    "boto3>=1.42.0",
    "google-auth>=2.0",
]

EXTRA_PACKAGES = ["./compliance_agent"]

AGENT_PLATFORM_CONFIG = {
    "identity_type": "AGENT_IDENTITY",
    "agent_gateway_config": {
        "agent_to_anywhere_config": {
            "agent_gateway": AGENT_GATEWAY,
        }
    },
}

CONFIG_PATH = "compliance_agent/.agent_engine_config.json"


def main() -> None:
    parser = argparse.ArgumentParser(description="Deploy Compliance agent to Agent Engine")
    parser.add_argument("--update", action="store_true", help="Update existing agent")
    args = parser.parse_args()

    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket=STAGING_BUCKET)
    client = vertexai.Client(project=PROJECT, location=LOCATION, http_options=dict(api_version="v1beta1"))

    sys.path.insert(0, ".")
    from compliance_agent.agent import create_compliance_agent

    print(f"{'Updating' if args.update else 'Deploying'} Compliance & Reporting agent...")
    try:
        app = reasoning_engines.AdkApp(agent=create_compliance_agent(), enable_tracing=True)
        deploy_config = dict(
            staging_bucket=STAGING_BUCKET,
            requirements=REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name="Compliance & Reporting Agent",
            description="Cross-cloud regulatory intelligence via A2A to AWS AgentCore Runtime",
            env_vars={
                "GOOGLE_GENAI_USE_VERTEXAI": "True",
                "GOOGLE_CLOUD_AGENT_ENGINE_ENABLE_TELEMETRY": "true",
            },
            **AGENT_PLATFORM_CONFIG,
        )

        existing_name = None
        if args.update:
            try:
                with open(CONFIG_PATH) as f:
                    existing_name = json.load(f).get("compliance_reporting")
            except FileNotFoundError:
                pass

        if args.update and existing_name:
            engine = client.agent_engines.update(name=existing_name, agent=app, config=deploy_config)
        else:
            engine = client.agent_engines.create(agent=app, config=deploy_config)

        resource_name = engine.api_resource.name
        print(f"  OK  compliance_reporting: {resource_name}")

        config = {"compliance_reporting": resource_name}
        with open(CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nConfig saved to {CONFIG_PATH}")
        print(f"Add to backend .env: COMPLIANCE_AGENT_ENGINE_ID={resource_name}")

    except Exception as e:
        print(f"  FAIL  {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
