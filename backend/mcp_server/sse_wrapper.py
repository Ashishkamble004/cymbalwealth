"""
SSE HTTP Wrapper for NSE/BSE MCP Server
Exposes the stdio MCP server over HTTP+SSE so it runs on Cloud Run.
Also provides a /chat REST endpoint that uses Gemini function calling
to answer natural language stock queries directly.
"""

import os
import asyncio
import logging

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport

from server import app as mcp_app, TOOLS, call_tool_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nse-mcp-sse")

PROJECT_ID       = os.environ.get("GOOGLE_CLOUD_PROJECT", "general-ak")
LOCATION         = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")
APIGEE_PROXY_URL = os.environ.get("APIGEE_PROXY_URL")  # set to enable Apigee AI Gateway

http_app = FastAPI(
    title="NSE/BSE Market Data MCP Server",
    description="MCP server + chat API for Indian stock market data",
    version="1.0.0",
)

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


# ── Gemini function declarations (derived from MCP TOOLS to avoid drift) ──────
# Each MCP Tool's inputSchema is structurally identical to a Gemini
# FunctionDeclaration's parameters field, so we map directly.

GEMINI_TOOLS = [
    {"name": t.name, "description": t.description, "parameters": t.inputSchema}
    for t in TOOLS
]

SYSTEM_PROMPT = """You are an expert Indian stock market analyst assistant for Cymbal Wealth.
You have access to live NSE and BSE market data tools.

Guidelines:
- Always fetch fresh data using tools before answering market questions
- Lead with the current price and % change when asked about a stock
- Use ₹ for Indian Rupee, Cr for Crores
- Flag when markets are closed (weekends/holidays) and data may be delayed
- Add context: relate numbers to sector trends or index performance
- This is for informational purposes only, not financial advice"""


@http_app.post("/chat")
async def chat_endpoint(request: Request):
    """
    REST chat endpoint. Accepts { query: str } and returns { response: str }.
    Uses Gemini function calling to dispatch NSE/BSE market data tools.
    """
    try:
        body  = await request.json()
        query = body.get("query", "").strip()
        if not query:
            return JSONResponse({"error": "query is required"}, status_code=400)

        response_text = await asyncio.to_thread(_run_gemini_chat, query)
        return JSONResponse({"response": response_text})

    except Exception as e:
        logger.error(f"Chat endpoint error: {e}", exc_info=True)
        return JSONResponse({"error": str(e)}, status_code=500)


def _run_gemini_chat(query: str) -> str:
    """Runs Gemini function-calling loop synchronously (called via to_thread).

    Routes through Apigee AI Gateway when APIGEE_PROXY_URL is set (token telemetry,
    audit logging, gemini-2.0 deny policy). Falls back to direct Vertex AI otherwise.
    """
    if APIGEE_PROXY_URL:
        return _run_via_apigee(query)
    return _run_direct(query)


def _run_via_apigee(query: str) -> str:
    """Chat via Apigee AI Gateway using ApigeeLlm + ADK runner."""
    from google.adk.models.apigee_llm import ApigeeLlm
    from google.adk.agents import LlmAgent
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    # Import the 8 tool handler functions from server.py to pass as ADK tools
    from server import (
        handle_get_stock_quote, handle_get_index_data, handle_get_historical_data,
        handle_compare_stocks, handle_get_top_movers, handle_get_sector_performance,
        handle_get_company_info, handle_get_financials,
    )

    # Thin wrapper functions with ADK-compatible signatures
    def get_stock_quote(symbol: str, exchange: str = "NSE") -> str:
        """Get real-time quote for an NSE/BSE listed stock."""
        return handle_get_stock_quote(symbol, exchange)

    def get_index_data(index: str) -> str:
        """Get current value for a major Indian index: NIFTY50, SENSEX, NIFTYBANK, NIFTYIT, NIFTYMIDCAP."""
        return handle_get_index_data(index)

    def get_historical_data(symbol: str, period: str = "1mo", exchange: str = "NSE") -> str:
        """Get historical OHLCV data for a stock. period: 1w/1mo/3mo/6mo/1y/2y/5y."""
        return handle_get_historical_data(symbol, period, exchange)

    def compare_stocks(symbols: list) -> str:
        """Compare 2-5 NSE/BSE stocks side-by-side."""
        return handle_compare_stocks(symbols)

    def get_top_movers(type: str = "both", top_n: int = 5) -> str:
        """Get top gainers/losers from Nifty 50. type: gainers/losers/both."""
        return handle_get_top_movers(type, top_n)

    def get_sector_performance() -> str:
        """Get today's performance for IT, Banking, Pharma, Auto, FMCG, Energy, Metals."""
        return handle_get_sector_performance()

    def get_company_info(symbol: str) -> str:
        """Get company info: sector, industry, employees, HQ, business summary."""
        return handle_get_company_info(symbol)

    def get_financials(symbol: str) -> str:
        """Get key financials: revenue, profit, ROE, debt/equity, dividend yield."""
        return handle_get_financials(symbol)

    apigee_model = ApigeeLlm(
        model="apigee/vertex_ai/gemini-2.5-flash",
        proxy_url=APIGEE_PROXY_URL,
        custom_headers={"x-cymbal-app": "investments-chat"},
    )
    agent = LlmAgent(
        model=apigee_model,
        name="investments_chat_agent",
        instruction=SYSTEM_PROMPT,
        tools=[get_stock_quote, get_index_data, get_historical_data, compare_stocks,
               get_top_movers, get_sector_performance, get_company_info, get_financials],
    )

    import asyncio
    loop = asyncio.new_event_loop()
    try:
        return loop.run_until_complete(_run_adk_agent(agent, query))
    finally:
        loop.close()


async def _run_adk_agent(agent, query: str) -> str:
    from google.adk.runners import Runner
    from google.adk.sessions import InMemorySessionService
    from google.genai import types as genai_types

    session_svc = InMemorySessionService()
    runner      = Runner(agent=agent, app_name="investments", session_service=session_svc)
    session     = await session_svc.create_session(app_name="investments", user_id="chat")
    content     = genai_types.Content(role="user", parts=[genai_types.Part(text=query)])

    async for event in runner.run_async(
        user_id="chat", session_id=session.id, new_message=content
    ):
        if event.is_final_response() and event.content:
            return "\n".join(
                p.text for p in event.content.parts if hasattr(p, "text") and p.text
            ).strip()
    return ""


def _run_direct(query: str) -> str:
    """Chat directly via Vertex AI (no Apigee) — used when APIGEE_PROXY_URL is unset."""
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)
    tools  = [types.Tool(function_declarations=[
        types.FunctionDeclaration(**t) for t in GEMINI_TOOLS
    ])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT, tools=tools, temperature=0.1,
    )
    messages = [types.Content(role="user", parts=[types.Part(text=query)])]

    for _ in range(5):
        response       = client.models.generate_content(model="gemini-2.5-flash", contents=messages, config=config)
        candidate      = response.candidates[0]
        messages.append(candidate.content)
        function_calls = [p for p in candidate.content.parts if p.function_call]
        if not function_calls:
            break
        fn_responses = []
        for part in function_calls:
            fc   = part.function_call
            args = dict(fc.args) if fc.args else {}
            logger.info(f"Tool call: {fc.name}({args})")
            fn_responses.append(
                types.Part.from_function_response(name=fc.name, response={"result": call_tool_handler(fc.name, args)})
            )
        messages.append(types.Content(role="user", parts=fn_responses))

    final_parts = response.candidates[0].content.parts
    return "\n".join(p.text for p in final_parts if hasattr(p, "text") and p.text).strip()


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
