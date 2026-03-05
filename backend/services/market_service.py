"""
Market Service — market data and benchmark context
"""

import logging
from datetime import date

logger = logging.getLogger(__name__)


def get_market_summary() -> str:
    """Return a market context summary for Gemini prompts.

    In production, this would integrate with a real market data provider.
    For the prototype, we return a realistic static summary.
    """
    today = date.today().isoformat()
    return (
        f"As of {today}: Nifty 50 is at 24,857 (+2.3% MTD, +14.1% YTD). "
        "Sensex at 81,721. India VIX at 13.2 (low volatility). "
        "10Y G-Sec yield at 7.12%. INR/USD at 83.42. "
        "FII flows: net sellers ₹-3,200 Cr MTD. DII flows: net buyers ₹+5,100 Cr MTD. "
        "Sector performance MTD: IT +4.1%, Banking +1.8%, Pharma +3.2%, Auto -0.5%, Realty -1.2%. "
        "RBI policy rate unchanged at 6.50%. Crude oil (Brent) at $78.4/bbl. "
        "Gold at ₹72,400/10g (+1.5% MTD). "
        "Key events: Q3 earnings season underway; Union Budget expectations driving mid-cap rally."
    )


def get_nifty_return_mtd() -> float:
    """Return the Nifty 50 month-to-date return percentage."""
    return 2.3


def get_nifty_return_ytd() -> float:
    """Return the Nifty 50 year-to-date return percentage."""
    return 14.1
