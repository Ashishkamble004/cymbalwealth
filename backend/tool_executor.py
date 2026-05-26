"""Cymbal Wealth — Non-blocking Tool Call Executor (genai-sdk).

Handles tool calls from the Gemini Live session, sends an interim
"PROCESSING" response immediately, then executes the real tool function
in a background task and sends the final result back to the model.

Adapted from kkrishnan90/gemini-mm-live-demo pattern.
"""

import asyncio
import hashlib
import json
import logging
import time

from google.genai import types

logger = logging.getLogger(__name__)

DEDUP_WINDOW_SEC = 2.0


class ToolExecutor:
    """Execute tool calls non-blocking with deduplication."""

    def __init__(self, tools_map: dict):
        self.tools_map = tools_map
        self.session = None  # Set after session is created
        self.recent_calls: dict[str, float] = {}

    async def handle_tool_call(self, tool_call):
        """Handle tool call non-blocking -- send interim response, execute in background."""
        for fc in tool_call.function_calls:
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            call_id = fc.id

            # Dedup check
            args_str = json.dumps(args, sort_keys=True)
            dedup_key = f"{name}:{hashlib.md5(args_str.encode()).hexdigest()[:8]}"
            now = time.time()
            if now - self.recent_calls.get(dedup_key, 0) < DEDUP_WINDOW_SEC:
                logger.warning(
                    "Duplicate tool call %s within %ss, skipping", name, DEDUP_WINDOW_SEC
                )
                continue
            self.recent_calls[dedup_key] = now

            logger.info("Tool call: %s(%s) -- executing in background", name, args)

            # Execute in background
            asyncio.create_task(self._execute_and_respond(name, args, call_id))

    async def _execute_and_respond(self, name: str, args: dict, call_id: str):
        """Run the tool function and send the result back to the session."""
        handler = self.tools_map.get(name)
        if not handler:
            logger.error("Unknown tool: %s", name)
            return
        try:
            result = await asyncio.to_thread(handler, **args)
            if not isinstance(result, dict):
                result = {"result": str(result)}
            await self.session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(name=name, id=call_id, response=result)
                ]
            )
            logger.info("Tool %s completed successfully", name)
        except Exception as e:
            logger.error("Tool %s failed: %s", name, e)
            await self.session.send_tool_response(
                function_responses=[
                    types.FunctionResponse(
                        name=name,
                        id=call_id,
                        response={"error": str(e), "status": "ERROR"},
                    )
                ]
            )
