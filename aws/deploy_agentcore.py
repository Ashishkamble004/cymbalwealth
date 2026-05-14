#!/usr/bin/env python3
"""Deploy CymbalWealth A2A agents to Bedrock AgentCore Runtime.

Usage:
    # Set AWS MFA session credentials first, then:
    python deploy_agentcore.py [credit|regulatory|both]

    # Default deploys both agents.
"""

import os
import sys

from bedrock_agentcore_starter_toolkit import Runtime
from boto3.session import Session

REGION = os.environ.get("AWS_REGION", "us-east-1")
REDSHIFT_SECRET_ARN = os.environ.get(
    "REDSHIFT_SECRET_ARN",
    "arn:aws:secretsmanager:us-east-1:453809273083:secret:cymbal-wealth-redshift-admin-8IrLcy",
)

AGENTS = {
    "credit": {
        "name": "cymbal_credit_intelligence",
        "entrypoint": "credit_intelligence/app.py",
        "requirements": "requirements-agentcore.txt",
    },
    "regulatory": {
        "name": "cymbal_regulatory_reporting",
        "entrypoint": "regulatory_reporting/app.py",
        "requirements": "requirements-agentcore.txt",
    },
}


def deploy_agent(key: str) -> None:
    agent_cfg = AGENTS[key]
    print(f"\n{'='*60}")
    print(f"Deploying: {agent_cfg['name']}")
    print(f"Entrypoint: {agent_cfg['entrypoint']}")
    print(f"Region: {REGION}")
    print(f"{'='*60}\n")

    runtime = Runtime()
    runtime.configure(
        entrypoint=agent_cfg["entrypoint"],
        auto_create_execution_role=True,
        auto_create_ecr=True,
        requirements_file=agent_cfg["requirements"],
        region=REGION,
        protocol="A2A",
        agent_name=agent_cfg["name"],
    )

    env_vars = {
        "REDSHIFT_WORKGROUP": "cymbal-wealth-wg",
        "REDSHIFT_DATABASE": "cymbalwealth",
        "REDSHIFT_SECRET_ARN": REDSHIFT_SECRET_ARN,
        "BEDROCK_REGION": REGION,
    }

    result = runtime.launch(env_vars=env_vars)
    print(f"\nAgent ARN: {result.agent_arn}")
    print(f"Agent URL: https://bedrock-agentcore.{REGION}.amazonaws.com/runtimes/{result.agent_arn}/invocations/")
    return result


def main():
    target = sys.argv[1] if len(sys.argv) > 1 else "both"

    if target == "credit":
        deploy_agent("credit")
    elif target == "regulatory":
        deploy_agent("regulatory")
    elif target == "both":
        deploy_agent("credit")
        deploy_agent("regulatory")
    else:
        print(f"Unknown target: {target}. Use: credit, regulatory, or both")
        sys.exit(1)


if __name__ == "__main__":
    main()
