"""Cymbal Wealth — Video KYC Agent package.

Uses AgentTool pattern for calling sub-agents:
- Root agent: Live API (gemini-live-2.5-flash-preview-native-audio) for voice/video KYC
- Sub-agents: Text model (gemini-2.5-flash) for document verification
"""

from .agent import agent

__all__ = ["agent"]
