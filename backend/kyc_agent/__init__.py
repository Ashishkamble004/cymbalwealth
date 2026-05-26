"""Cymbal Wealth — Video KYC Agent package (genai-sdk).

Exports the system instruction, tool declarations, and tool implementations
for the Gemini Live session managed by gemini_client.py + tool_executor.py.
"""

from .agent import SYSTEM_INSTRUCTION, get_tool_declarations
from .sub_agents.verification_agent import TOOLS_MAP

__all__ = ["SYSTEM_INSTRUCTION", "get_tool_declarations", "TOOLS_MAP"]
