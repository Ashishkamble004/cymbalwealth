"""Deploy Compliance & Reporting agent to Vertex AI Agent Engine.

Usage:
    cd backend
    python -m compliance_agent.deploy
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
    "google-cloud-aiplatform",
    "vertexai",
    "requests",
    "boto3>=1.42.0",
]

EXTRA_PACKAGES = ["./compliance_agent"]


def main() -> None:
    vertexai.init(project=PROJECT, location=LOCATION, staging_bucket="gs://cymbal-wealth-staging")
    sys.path.insert(0, ".")
    from compliance_agent.agent import create_compliance_agent

    print("Deploying Compliance & Reporting agent...")
    try:
        app = reasoning_engines.AdkApp(agent=create_compliance_agent(), enable_tracing=True)
        remote = reasoning_engines.ReasoningEngine.create(
            app,
            requirements=REQUIREMENTS,
            extra_packages=EXTRA_PACKAGES,
            display_name="Compliance & Reporting Agent",
            description="Cross-cloud regulatory intelligence via A2A to AWS AgentCore Runtime",
        )
        resource_name = remote.resource_name
        print(f"  OK  compliance_reporting: {resource_name}")

        config = {"compliance_reporting": resource_name}
        config_path = "compliance_agent/.agent_engine_config.json"
        with open(config_path, "w") as f:
            json.dump(config, f, indent=2)
        print(f"\nConfig saved to {config_path}")
        print(f"Add to backend .env: COMPLIANCE_AGENT_ENGINE_ID={resource_name}")

    except Exception as e:
        print(f"  FAIL  {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
