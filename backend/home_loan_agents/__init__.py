"""Cymbal Wealth — Home Loan Document Verification Agents.

Optimized pipeline using ParallelAgent + SequentialAgent:
- Step 1 (Parallel): Doc Quality + Identity/Income
- Step 2 (Sequential): Property/Eligibility

3 LLM calls instead of 6. Parallel execution where possible.
"""

from .orchestrator import orchestrator_agent

__all__ = ["orchestrator_agent"]
