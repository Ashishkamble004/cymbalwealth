"""
SSE HTTP Wrapper for NSE/BSE MCP Server
Exposes the stdio MCP server over HTTP+SSE so it runs on Cloud Run.
Also provides a /chat REST endpoint that uses Gemini function calling
to answer natural language stock queries directly.
"""

import os
import asyncio
import logging
from typing import Any

import uvicorn
from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from fastapi.middleware.cors import CORSMiddleware
from mcp.server.sse import SseServerTransport

from server import app as mcp_app, TOOLS, call_tool_handler

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("nse-mcp-sse")

PROJECT_ID = os.environ.get("GOOGLE_CLOUD_PROJECT", "general-ak")
LOCATION   = os.environ.get("GOOGLE_CLOUD_LOCATION", "us-central1")

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


# ── Gemini function declarations (mirrors MCP TOOLS) ─────────────────────────

GEMINI_TOOLS = [
    {
        "name": "get_stock_quote",
        "description": "Get real-time quote for an NSE/BSE listed stock. Returns price, change, volume, market cap, P/E ratio, 52-week range.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE stock symbol e.g. RELIANCE, TCS, INFY, HDFCBANK"},
                "exchange": {"type": "string", "enum": ["NSE", "BSE"], "description": "Exchange (default: NSE)"}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "get_index_data",
        "description": "Get current value and change for major Indian indices: NIFTY50, SENSEX, NIFTYBANK, NIFTYIT, NIFTYMIDCAP.",
        "parameters": {
            "type": "object",
            "properties": {
                "index": {"type": "string", "enum": ["NIFTY50", "SENSEX", "NIFTYBANK", "NIFTYIT", "NIFTYMIDCAP"]}
            },
            "required": ["index"]
        }
    },
    {
        "name": "get_historical_data",
        "description": "Get historical OHLCV data for a stock. Useful for trend analysis.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "period": {"type": "string", "enum": ["1w", "1mo", "3mo", "6mo", "1y", "2y", "5y"]},
                "exchange": {"type": "string", "enum": ["NSE", "BSE"]}
            },
            "required": ["symbol"]
        }
    },
    {
        "name": "compare_stocks",
        "description": "Compare multiple NSE/BSE stocks side-by-side on price, market cap, P/E, dividend yield, 52-week performance.",
        "parameters": {
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}, "description": "List of NSE symbols e.g. ['TCS','INFY','WIPRO']"}
            },
            "required": ["symbols"]
        }
    },
    {
        "name": "get_top_movers",
        "description": "Get top gainers and losers from Nifty 50 for today.",
        "parameters": {
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["gainers", "losers", "both"]},
                "top_n": {"type": "integer"}
            }
        }
    },
    {
        "name": "get_sector_performance",
        "description": "Get performance of Indian market sectors: IT, Banking, Pharma, Auto, FMCG, Energy, Metals.",
        "parameters": {"type": "object", "properties": {}}
    },
    {
        "name": "get_company_info",
        "description": "Get detailed company information: business summary, sector, industry, employees, headquarters.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"]
        }
    },
    {
        "name": "get_financials",
        "description": "Get key financial metrics: revenue, profit, EPS, ROE, debt-to-equity, cash flow.",
        "parameters": {
            "type": "object",
            "properties": {"symbol": {"type": "string"}},
            "required": ["symbol"]
        }
    },
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
    """Runs Gemini function-calling loop synchronously (called via to_thread)."""
    from google import genai
    from google.genai import types

    client = genai.Client(vertexai=True, project=PROJECT_ID, location=LOCATION)

    tools = [types.Tool(function_declarations=[
        types.FunctionDeclaration(**t) for t in GEMINI_TOOLS
    ])]
    config = types.GenerateContentConfig(
        system_instruction=SYSTEM_PROMPT,
        tools=tools,
        temperature=0.1,
    )

    # Multi-turn function calling loop
    messages = [types.Content(role="user", parts=[types.Part(text=query)])]

    for _ in range(5):  # max 5 tool calls per query
        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=messages,
            config=config,
        )

        candidate = response.candidates[0]
        messages.append(candidate.content)  # add model turn

        # Check for function calls
        function_calls = [p for p in candidate.content.parts if p.function_call]
        if not function_calls:
            break

        # Execute all function calls and collect responses
        fn_responses = []
        for part in function_calls:
            fc   = part.function_call
            name = fc.name
            args = dict(fc.args) if fc.args else {}
            logger.info(f"Tool call: {name}({args})")
            result = call_tool_handler(name, args)
            fn_responses.append(
                types.Part.from_function_response(
                    name=name,
                    response={"result": result}
                )
            )

        messages.append(types.Content(role="user", parts=fn_responses))

    # Extract final text response
    final_parts = response.candidates[0].content.parts
    return "\n".join(p.text for p in final_parts if hasattr(p, "text") and p.text).strip()


# ── Standard utility endpoints ────────────────────────────────────────────────

@http_app.get("/health")
async def health():
    return {"status": "healthy", "server": "nse-bse-mcp", "version": "1.0.0"}


@http_app.get("/tools")
async def list_tools_endpoint():
    from server import TOOLS
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
