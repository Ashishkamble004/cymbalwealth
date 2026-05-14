"""Orchestrator Agent — Optimized multi-agent home loan verification pipeline.

Uses ParallelAgent + SequentialAgent for maximum throughput:
- Step 1 (Parallel): Doc Quality + Identity/Income + Credit Intelligence run simultaneously
- Step 2 (Sequential): Property/Eligibility runs after (needs income + credit data)

Credit Intelligence step calls AWS Bedrock via A2A protocol for CIBIL scoring.
"""

from google.adk.agents import Agent, SequentialAgent, ParallelAgent

from .sub_agents.doc_quality_agent import doc_quality_agent
from .sub_agents.identity_income_agent import identity_income_agent
from .sub_agents.property_eligibility_agent import property_eligibility_agent
from .sub_agents.credit_intelligence_agent import credit_intelligence_agent


# Step 1: Run doc quality, identity/income, AND credit intelligence IN PARALLEL
parallel_verification = ParallelAgent(
    name="parallel_verification",
    description="Runs document quality, identity/income, and credit intelligence checks simultaneously",
    sub_agents=[doc_quality_agent, identity_income_agent, credit_intelligence_agent],
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
