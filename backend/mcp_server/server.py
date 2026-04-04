"""
NSE/BSE MCP Server
Wraps public Indian stock market data (via yfinance)
and exposes it as MCP tools for AI agents on Google Cloud.
No API key required for demo use.
"""

import json
import asyncio
from datetime import datetime, timedelta
from typing import Any

import yfinance as yf
import pandas as pd
from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent

app = Server("nse-bse-market-server")

# ── helpers ───────────────────────────────────────────────────────────────────

def nse(symbol: str) -> str:
    return symbol.upper() + ".NS" if not symbol.endswith((".NS", ".BO")) else symbol

def bse(symbol: str) -> str:
    return symbol.upper() + ".BO" if not symbol.endswith((".NS", ".BO")) else symbol

def fmt(val: Any, decimals: int = 2) -> str:
    if isinstance(val, float):
        return f"{val:,.{decimals}f}"
    return str(val) if val is not None else "N/A"

def crore(val: Any) -> str:
    if isinstance(val, (int, float)) and val:
        return f"₹{val/1e7:,.2f} Cr"
    return "N/A"

def fmt_int(val: Any) -> str:
    """Format an integer value with commas; returns N/A for None/non-numeric."""
    if isinstance(val, (int, float)):
        return f"{int(val):,}"
    return "N/A"

# ── tool definitions ──────────────────────────────────────────────────────────

TOOLS = [
    Tool(
        name="get_stock_quote",
        description="Get real-time quote for an NSE/BSE listed stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string", "description": "NSE stock symbol e.g. RELIANCE, TCS, INFY"},
                "exchange": {"type": "string", "enum": ["NSE", "BSE"], "default": "NSE"}
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_index_data",
        description="Get current value and change for major Indian indices.",
        inputSchema={
            "type": "object",
            "properties": {
                "index": {"type": "string", "enum": ["NIFTY50", "SENSEX", "NIFTYBANK", "NIFTYIT", "NIFTYMIDCAP"]}
            },
            "required": ["index"]
        }
    ),
    Tool(
        name="get_historical_data",
        description="Get historical OHLCV data for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"},
                "period": {"type": "string", "enum": ["1w", "1mo", "3mo", "6mo", "1y", "2y", "5y"], "default": "1mo"},
                "exchange": {"type": "string", "enum": ["NSE", "BSE"], "default": "NSE"}
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="compare_stocks",
        description="Compare multiple NSE/BSE stocks side-by-side.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbols": {"type": "array", "items": {"type": "string"}, "minItems": 2, "maxItems": 5}
            },
            "required": ["symbols"]
        }
    ),
    Tool(
        name="get_top_movers",
        description="Get top gainers and losers from Nifty 50 for today.",
        inputSchema={
            "type": "object",
            "properties": {
                "type": {"type": "string", "enum": ["gainers", "losers", "both"], "default": "both"},
                "top_n": {"type": "integer", "default": 5, "minimum": 1, "maximum": 10}
            }
        }
    ),
    Tool(
        name="get_sector_performance",
        description="Get performance of Indian market sectors today.",
        inputSchema={"type": "object", "properties": {}}
    ),
    Tool(
        name="get_company_info",
        description="Get detailed company information for an NSE/BSE stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"}
            },
            "required": ["symbol"]
        }
    ),
    Tool(
        name="get_financials",
        description="Get key financial metrics for a stock.",
        inputSchema={
            "type": "object",
            "properties": {
                "symbol": {"type": "string"}
            },
            "required": ["symbol"]
        }
    ),
]

INDEX_TICKERS = {
    "NIFTY50":     "^NSEI",
    "SENSEX":      "^BSESN",
    "NIFTYBANK":   "^NSEBANK",
    "NIFTYIT":     "^CNXIT",
    "NIFTYMIDCAP": "^NSEMDCP50",
}

NIFTY50_SYMBOLS = [
    "RELIANCE", "TCS", "HDFCBANK", "INFY", "ICICIBANK",
    "HINDUNILVR", "ITC", "SBIN", "BAJFINANCE", "BHARTIARTL",
    "KOTAKBANK", "LT", "ASIANPAINT", "AXISBANK", "MARUTI",
    "SUNPHARMA", "TITAN", "ULTRACEMCO", "NESTLEIND", "WIPRO",
]

SECTOR_ETFS = {
    "IT":      "^CNXIT",
    "Banking": "^NSEBANK",
    "Pharma":  "NIFTYPHARMA.NS",
    "Auto":    "NIFTYAUTO.NS",
    "FMCG":    "^CNXFMCG",
    "Energy":  "NIFTYENERGY.NS",
    "Metals":  "NIFTYMETAL.NS",
}

# ── tool handlers ─────────────────────────────────────────────────────────────

def handle_get_stock_quote(symbol: str, exchange: str = "NSE") -> str:
    ticker_sym = nse(symbol) if exchange == "NSE" else bse(symbol)
    ticker = yf.Ticker(ticker_sym)
    info = ticker.info
    hist = ticker.history(period="2d")

    if hist.empty:
        return f"❌ No data found for {symbol} on {exchange}. Check the symbol and try again."

    prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else hist["Close"].iloc[-1]
    current    = hist["Close"].iloc[-1]
    change     = current - prev_close
    pct_change = (change / prev_close) * 100
    arrow      = "▲" if change >= 0 else "▼"
    color_tag  = "🟢" if change >= 0 else "🔴"

    return f"""
📊 **{info.get('longName', symbol)} ({symbol}) — {exchange}**
{color_tag} ₹{fmt(current)} {arrow} {fmt(change)} ({fmt(pct_change)}%) today

💰 **Price Info**
  • Open:           ₹{fmt(info.get('open', hist['Open'].iloc[-1]))}
  • Day High:       ₹{fmt(info.get('dayHigh', hist['High'].iloc[-1]))}
  • Day Low:        ₹{fmt(info.get('dayLow',  hist['Low'].iloc[-1]))}
  • Previous Close: ₹{fmt(prev_close)}
  • 52W High:       ₹{fmt(info.get('fiftyTwoWeekHigh'))}
  • 52W Low:        ₹{fmt(info.get('fiftyTwoWeekLow'))}

📈 **Valuation**
  • Market Cap:     {crore(info.get('marketCap'))}
  • P/E Ratio:      {fmt(info.get('trailingPE'))}x
  • EPS (TTM):      ₹{fmt(info.get('trailingEps'))}
  • Book Value:     ₹{fmt(info.get('bookValue'))}
  • Div Yield:      {fmt(info.get('dividendYield', 0) * 100)}%

📦 **Volume**
  • Volume:         {fmt_int(info.get('volume'))} shares
  • Avg Volume:     {fmt_int(info.get('averageVolume'))} shares

🏭 Sector: {info.get('sector', 'N/A')} | Industry: {info.get('industry', 'N/A')}
⏰ Last updated: {datetime.now().strftime('%d %b %Y %H:%M IST')}
""".strip()


def handle_get_index_data(index: str) -> str:
    ticker_sym = INDEX_TICKERS.get(index)
    if not ticker_sym:
        return f"❌ Unknown index: {index}"

    ticker = yf.Ticker(ticker_sym)
    hist   = ticker.history(period="2d")

    if hist.empty:
        return f"❌ Could not fetch data for {index}"

    current    = hist["Close"].iloc[-1]
    prev_close = hist["Close"].iloc[-2] if len(hist) >= 2 else current
    change     = current - prev_close
    pct_change = (change / prev_close) * 100
    arrow      = "▲" if change >= 0 else "▼"
    emoji      = "🟢" if change >= 0 else "🔴"

    return f"""
📊 **{index}**
{emoji} {fmt(current, 0)} pts {arrow} {fmt(change, 0)} ({fmt(pct_change)}%) today

  • Day High:  {fmt(hist['High'].iloc[-1], 0)}
  • Day Low:   {fmt(hist['Low'].iloc[-1], 0)}
  • Volume:    {fmt_int(hist['Volume'].iloc[-1])}
⏰ {datetime.now().strftime('%d %b %Y %H:%M IST')}
""".strip()


def handle_get_historical_data(symbol: str, period: str = "1mo", exchange: str = "NSE") -> str:
    period_map = {"1w": "7d", "1mo": "1mo", "3mo": "3mo", "6mo": "6mo", "1y": "1y", "2y": "2y", "5y": "5y"}
    yf_period  = period_map.get(period, "1mo")
    ticker_sym = nse(symbol) if exchange == "NSE" else bse(symbol)
    hist       = yf.Ticker(ticker_sym).history(period=yf_period)

    if hist.empty:
        return f"❌ No historical data for {symbol}"

    first_close = hist["Close"].iloc[0]
    last_close  = hist["Close"].iloc[-1]
    total_ret   = ((last_close - first_close) / first_close) * 100
    high        = hist["High"].max()
    low         = hist["Low"].min()
    avg_vol     = hist["Volume"].mean()

    closes = hist["Close"].tail(10).tolist()
    mn, mx = min(closes), max(closes)
    bars   = "▁▂▃▄▅▆▇█"
    spark  = "".join(bars[int((c - mn) / (mx - mn + 0.001) * 7)] for c in closes) if mx > mn else "────"

    rows = "\n".join(
        f"  {d.strftime('%d %b')}: ₹{fmt(r['Open'])} → ₹{fmt(r['Close'])}  Vol: {fmt_int(r['Volume'])}"
        for d, r in hist.tail(5).iterrows()
    )

    return f"""
📈 **{symbol} ({exchange}) — {period} Historical Data**

  Sparkline (last 10 sessions): {spark}

📊 Summary
  • Period Return:  {'+' if total_ret >= 0 else ''}{fmt(total_ret)}%
  • Period High:   ₹{fmt(high)}
  • Period Low:    ₹{fmt(low)}
  • Avg Volume:    {fmt_int(avg_vol)} shares

📅 Last 5 Sessions
{rows}
""".strip()


def handle_compare_stocks(symbols: list) -> str:
    rows = []
    headers = ["Symbol", "Price (₹)", "Change%", "Mkt Cap", "P/E", "52W Ret%", "Div Yield"]
    rows.append(" | ".join(f"{h:<12}" for h in headers))
    rows.append("-" * 85)

    for sym in symbols:
        try:
            ticker = yf.Ticker(nse(sym))
            info   = ticker.info
            hist   = ticker.history(period="1y")

            price  = info.get("currentPrice") or info.get("regularMarketPrice", 0)
            change = info.get("regularMarketChangePercent", 0)
            mc     = crore(info.get("marketCap"))
            pe     = fmt(info.get("trailingPE"))
            dy     = f"{fmt(info.get('dividendYield', 0)*100)}%"

            if not hist.empty:
                ret_52w = ((hist["Close"].iloc[-1] - hist["Close"].iloc[0]) / hist["Close"].iloc[0]) * 100
                ret_str = f"{'+' if ret_52w >= 0 else ''}{fmt(ret_52w)}%"
            else:
                ret_str = "N/A"

            row = [sym, f"₹{fmt(price)}", f"{'+' if change>=0 else ''}{fmt(change)}%", mc, pe, ret_str, dy]
            rows.append(" | ".join(f"{str(v):<12}" for v in row))
        except Exception as e:
            rows.append(f"{sym:<12} | Error fetching data")

    return f"""
🔍 **Stock Comparison — NSE**
⏰ {datetime.now().strftime('%d %b %Y %H:%M IST')}

{chr(10).join(rows)}

📌 Data sourced from Yahoo Finance (NSE). For investment decisions, verify with official NSE/BSE feeds.
""".strip()


def handle_get_top_movers(type_: str = "both", top_n: int = 5) -> str:
    results = []
    for sym in NIFTY50_SYMBOLS:
        try:
            hist = yf.Ticker(nse(sym)).history(period="2d")
            if len(hist) >= 2:
                chg = ((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2]) * 100
                results.append((sym, hist["Close"].iloc[-1], chg))
        except Exception:
            pass

    results.sort(key=lambda x: x[2], reverse=True)
    gainers = results[:top_n]
    losers  = results[-top_n:][::-1]

    def fmt_list(items, emoji):
        return "\n".join(
            f"  {emoji} {sym:<14} ₹{fmt(price):<10} {'+' if chg>=0 else ''}{fmt(chg)}%"
            for sym, price, chg in items
        )

    out = f"📊 **Nifty 50 Top Movers — {datetime.now().strftime('%d %b %Y')}**\n"
    if type_ in ("gainers", "both"):
        out += f"\n🟢 **Top {top_n} Gainers**\n{fmt_list(gainers, '📈')}\n"
    if type_ in ("losers", "both"):
        out += f"\n🔴 **Top {top_n} Losers**\n{fmt_list(losers, '📉')}\n"
    return out.strip()


def handle_get_sector_performance() -> str:
    rows = ["🏭 **Indian Market Sector Performance**", f"⏰ {datetime.now().strftime('%d %b %Y %H:%M IST')}\n"]
    for sector, ticker_sym in SECTOR_ETFS.items():
        try:
            hist = yf.Ticker(ticker_sym).history(period="2d")
            if len(hist) >= 2:
                chg = ((hist["Close"].iloc[-1] - hist["Close"].iloc[-2]) / hist["Close"].iloc[-2]) * 100
                bar = "🟢" if chg >= 0 else "🔴"
                rows.append(f"  {bar} {sector:<10} {'+' if chg>=0 else ''}{fmt(chg)}%  ({fmt(hist['Close'].iloc[-1], 0)} pts)")
            else:
                rows.append(f"  ⚪ {sector:<10} N/A")
        except Exception:
            rows.append(f"  ⚪ {sector:<10} Error")
    return "\n".join(rows)


def handle_get_company_info(symbol: str) -> str:
    info = yf.Ticker(nse(symbol)).info
    employees = info.get('fullTimeEmployees')
    emp_str = f"{int(employees):,} full-time" if isinstance(employees, (int, float)) and employees else "N/A"
    return f"""
🏢 **{info.get('longName', symbol)}**

📋 Overview
  • Symbol:      {symbol} (NSE) / {info.get('exchange', 'N/A')}
  • Sector:      {info.get('sector', 'N/A')}
  • Industry:    {info.get('industry', 'N/A')}
  • Employees:   {emp_str}
  • HQ:          {info.get('city', '')}, {info.get('country', 'N/A')}
  • Website:     {info.get('website', 'N/A')}

📝 Business Summary
{info.get('longBusinessSummary', 'No summary available.')[:600]}...
""".strip()


def handle_get_financials(symbol: str) -> str:
    ticker = yf.Ticker(nse(symbol))
    info   = ticker.info

    try:
        inc = ticker.financials
        rev = inc.loc["Total Revenue"].iloc[0] if "Total Revenue" in inc.index else None
        ni  = inc.loc["Net Income"].iloc[0]    if "Net Income"    in inc.index else None
    except Exception:
        rev, ni = None, None

    return f"""
💰 **{info.get('longName', symbol)} — Key Financials**

📊 Income
  • Revenue (TTM):     {crore(rev)}
  • Net Income (TTM):  {crore(ni)}
  • EPS (TTM):         ₹{fmt(info.get('trailingEps'))}
  • Profit Margin:     {fmt(info.get('profitMargins', 0)*100)}%
  • Revenue Growth:    {fmt(info.get('revenueGrowth', 0)*100)}%

📈 Returns & Efficiency
  • ROE:               {fmt(info.get('returnOnEquity', 0)*100)}%
  • ROA:               {fmt(info.get('returnOnAssets', 0)*100)}%
  • Operating Margin:  {fmt(info.get('operatingMargins', 0)*100)}%

🏦 Balance Sheet
  • Total Cash:        {crore(info.get('totalCash'))}
  • Total Debt:        {crore(info.get('totalDebt'))}
  • Debt/Equity:       {fmt(info.get('debtToEquity'))}x
  • Current Ratio:     {fmt(info.get('currentRatio'))}x

💸 Dividends
  • Dividend Yield:    {fmt(info.get('dividendYield', 0)*100)}%
  • Payout Ratio:      {fmt(info.get('payoutRatio', 0)*100)}%
""".strip()


# ── Tool dispatcher (used by both MCP and REST /chat) ─────────────────────────

def call_tool_handler(name: str, arguments: dict) -> str:
    try:
        if name == "get_stock_quote":
            return handle_get_stock_quote(arguments["symbol"], arguments.get("exchange", "NSE"))
        elif name == "get_index_data":
            return handle_get_index_data(arguments["index"])
        elif name == "get_historical_data":
            return handle_get_historical_data(
                arguments["symbol"], arguments.get("period", "1mo"), arguments.get("exchange", "NSE"))
        elif name == "compare_stocks":
            return handle_compare_stocks(arguments["symbols"])
        elif name == "get_top_movers":
            return handle_get_top_movers(arguments.get("type", "both"), arguments.get("top_n", 5))
        elif name == "get_sector_performance":
            return handle_get_sector_performance()
        elif name == "get_company_info":
            return handle_get_company_info(arguments["symbol"])
        elif name == "get_financials":
            return handle_get_financials(arguments["symbol"])
        else:
            return f"❌ Unknown tool: {name}"
    except Exception as e:
        return f"❌ Error executing {name}: {str(e)}"


# ── MCP request handlers ──────────────────────────────────────────────────────

@app.list_tools()
async def list_tools():
    return TOOLS


@app.call_tool()
async def call_tool(name: str, arguments: dict):
    result = call_tool_handler(name, arguments)
    return [TextContent(type="text", text=result)]


# ── entrypoint ────────────────────────────────────────────────────────────────

async def main():
    async with stdio_server() as (read_stream, write_stream):
        await app.run(read_stream, write_stream, app.create_initialization_options())

if __name__ == "__main__":
    asyncio.run(main())
