"""Orchestrator Agent — Optimized multi-agent home loan verification pipeline.

Uses ParallelAgent + SequentialAgent for maximum throughput:
- Step 1 (Parallel): Doc Quality + Identity/Income run simultaneously
- Step 2 (Sequential): Property/Eligibility runs after (needs income data)

Reduced from 7 LLM calls to 4 (1 orchestrator overhead + 3 sub-agents).
"""

import os
from google.adk.agents import Agent, SequentialAgent, ParallelAgent

from .sub_agents.doc_quality_agent import doc_quality_agent
from .sub_agents.identity_income_agent import identity_income_agent
from .sub_agents.property_eligibility_agent import property_eligibility_agent


# Step 1: Run doc quality check AND identity/income verification IN PARALLEL
parallel_verification = ParallelAgent(
    name="parallel_verification",
    description="Runs document quality check and identity/income verification simultaneously",
    sub_agents=[doc_quality_agent, identity_income_agent],
)

# Full pipeline: parallel checks first, then property/eligibility (needs income result)
orchestrator_agent = SequentialAgent(
    name="home_loan_orchestrator",
    description="Orchestrates the home loan document verification pipeline",
    sub_agents=[
        parallel_verification,
        property_eligibility_agent,
    ],
)
