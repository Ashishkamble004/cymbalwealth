"""
SSE HTTP Wrapper for NSE/BSE MCP Server
Exposes the stdio MCP server over HTTP+SSE so it runs on Cloud Run.
Also provides a /chat REST endpoint powered by an ADK Agent that
discovers tools via local MCP SSE self-connection.
"""

import os
import asyncio
import logging
import time

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport

from server import app as mcp_app, TOOLS

# ── Observability setup ──────────────────────────────────────────────────────
PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "general-ak")
LOCATION   = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
MCP_SERVER_NAME = os.environ.get(
    "MCP_SERVER_NAME",
    "agentregistry-00000000-0000-0000-4b8f-8f1258474497",
)

os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "True"

try:
    import google.cloud.logging as cloud_logging
    cloud_logging.Client(project=PROJECT_ID).setup_logging()
    logging.info("Cloud Logging configured")
except Exception:
    logging.basicConfig(level=logging.INFO)

logger = logging.getLogger("nse-mcp-sse")

try:
    from opentelemetry import trace
    from opentelemetry.sdk.trace import TracerProvider
    from opentelemetry.sdk.trace.export import BatchSpanProcessor
    from opentelemetry.exporter.cloud_trace import CloudTraceSpanExporter
    from opentelemetry.sdk.resources import Resource
    from opentelemetry.resourcedetector.gcp_resource_detector import GoogleCloudResourceDetector
    from opentelemetry.instrumentation.fastapi import FastAPIInstrumentator

    resource = Resource.create({
        "service.name": "nse-bse-mcp-server",
        "service.version": "1.0.0",
    }).merge(GoogleCloudResourceDetector().detect())

    provider = TracerProvider(resource=resource)
    provider.add_span_processor(BatchSpanProcessor(CloudTraceSpanExporter(project_id=PROJECT_ID)))
    trace.set_tracer_provider(provider)
    tracer = trace.get_tracer("nse-mcp-sse")
    _otel_enabled = True
    logger.info("OpenTelemetry tracing configured → Cloud Trace")
except Exception as e:
    logger.warning(f"OpenTelemetry setup failed, tracing disabled: {e}")
    tracer = None
    _otel_enabled = False

http_app = FastAPI(
    title="NSE/BSE Market Data MCP Server",
    description="MCP server + chat API for Indian stock market data",
    version="1.0.0",
)

if _otel_enabled:
    FastAPIInstrumentator.instrument_app(http_app)

http_app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── SSE transport (MCP protocol) ──────────────────────────────────────────────
# Use trailing slash on path to avoid 307 redirects swallowing POST bodies
sse_transport = SseServerTransport("/messages/")
http_app.mount("/messages/", sse_transport.handle_post_message)


@http_app.get("/sse")
async def sse_endpoint(request: Request):
    """SSE endpoint — MCP clients connect here."""
    async with sse_transport.connect_sse(
        request.scope, request.receive, request._send
    ) as streams:
        await mcp_app.run(
            streams[0], streams[1],
            mcp_app.create_initialization_options()
        )


# ── ADK Agent with Agent Registry MCP toolset ────────────────────────────────

SYSTEM_PROMPT = """You are an expert Indian stock market analyst assistant for Cymbal Wealth.
You have access to live NSE and BSE market data tools via the Agent Registry.

Guidelines:
- Always fetch fresh data using tools before answering market questions
- Lead with the current price and % change when asked about a stock
- Use ₹ for Indian Rupee, Cr for Crores
- Flag when markets are closed (weekends/holidays) and data may be delayed
- Add context: relate numbers to sector trends or index performance
- This is for informational purposes only, not financial advice"""

_agent = None
_agent_lock = asyncio.Lock()


async def _get_agent():
    """Lazily initialise the ADK Agent with local MCP toolset via SSE."""
    global _agent
    if _agent is not None:
        return _agent

    async with _agent_lock:
        if _agent is not None:
            return _agent

        from google.adk.agents import Agent
        from google.adk.models import Gemini
        from google.adk.tools.mcp_tool.mcp_toolset import McpToolset
        from google.adk.tools.mcp_tool.mcp_session_manager import SseConnectionParams
        from google.genai import types

        port = int(os.environ.get("PORT", 8080))
        mcp_toolset = McpToolset(
            connection_params=SseConnectionParams(url=f"http://localhost:{port}/sse"),
        )

        _agent = Agent(
            name="nse_bse_market_intelligence",
            description=SYSTEM_PROMPT,
            model=Gemini(
                model="gemini-2.5-flash",
                retry_options=types.HttpRetryOptions(attempts=3),
            ),
            tools=[mcp_toolset],
        )
        logger.info("ADK Agent initialised with local MCP toolset via SSE")
        return _agent


async def _run_agent_chat(query: str) -> str:
    """Run a single-turn ADK agent query and return the text response."""
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types
    import uuid

    agent = await _get_agent()
    session_service = InMemorySessionService()
    runner = Runner(
        app_name="nse-bse-chat",
        agent=agent,
        session_service=session_service,
    )

    user_id = "chat-user"
    session_id = f"chat-{uuid.uuid4().hex[:8]}"
    session = await session_service.create_session(
        app_name="nse-bse-chat", user_id=user_id, session_id=session_id,
    )

    content = types.Content(
        role="user", parts=[types.Part(text=query)]
    )

    final_text = []
    async for event in runner.run_async(
        user_id=user_id,
        session_id=session_id,
        new_message=content,
    ):
        if event.content and event.content.parts:
            for part in event.content.parts:
                if part.text:
                    final_text.append(part.text)

    return "\n".join(final_text).strip() or "No response from agent."


@http_app.post("/chat")
async def chat_endpoint(request: Request):
    """
    REST chat endpoint. Accepts { query: str } and returns { response: str }.
    Uses an ADK Agent backed by local MCP toolset via SSE.
    """
    start = time.monotonic()
    try:
        body  = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return JSONResponse({"error": "query is required"}, status_code=400)

        if tracer:
            with tracer.start_as_current_span("chat_query", attributes={
                "chat.query": query[:200],
                "mcp.server": MCP_SERVER_NAME,
            }) as span:
                response_text = await _run_agent_chat(query)
                span.set_attribute("chat.response_length", len(response_text))
                span.set_attribute("chat.latency_ms", int((time.monotonic() - start) * 1000))
        else:
            response_text = await _run_agent_chat(query)

        latency_ms = int((time.monotonic() - start) * 1000)
        logger.info("Chat query completed", extra={
            "query": query[:100],
            "response_length": len(response_text),
            "latency_ms": latency_ms,
        })
        return JSONResponse({"response": response_text})

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


# ── Standard utility endpoints ────────────────────────────────────────────────

@http_app.get("/health")
async def health():
    return {"status": "healthy", "server": "nse-bse-mcp", "version": "1.0.0"}


@http_app.get("/tools")
async def list_tools_endpoint():
    return {
        "tools": [
            {"name": t.name, "description": t.description, "parameters": t.inputSchema}
            for t in TOOLS
        ]
    }


@http_app.get("/")
async def root():
    return {
        "name": "NSE/BSE Market Data MCP Server",
        "mcp_endpoint": "/sse",
        "chat_endpoint": "/chat",
        "tools_endpoint": "/tools",
        "health_endpoint": "/health",
    }


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    logger.info(f"Starting NSE/BSE MCP Server on port {port}")
    uvicorn.run(http_app, host="0.0.0.0", port=port, log_level="info")
