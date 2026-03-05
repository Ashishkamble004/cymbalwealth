"""
Gemini AI Service — Unified interface for all Gemini API calls
"""

import json
import logging
from typing import AsyncGenerator

import google.generativeai as genai

from config import settings

logger = logging.getLogger(__name__)

# Configure the SDK
if settings.GEMINI_API_KEY:
    genai.configure(api_key=settings.GEMINI_API_KEY)


def _get_model(model_name: str | None = None):
    """Return a GenerativeModel instance."""
    name = model_name or settings.GEMINI_TEXT_MODEL
    return genai.GenerativeModel(name)


# ---------------------------------------------------------------------------
# Layer 1 — KYC Document Analysis
# ---------------------------------------------------------------------------

KYC_SYSTEM_PROMPT = """You are a KYC analyst at a private bank in India.
Extract from the uploaded documents: full name, date of birth, address,
PAN number, last 4 digits of Aadhaar, and annual income estimate.
Flag any inconsistencies, document tampering signs, or AML risk signals.
Return ONLY a strict JSON object — no explanation, no markdown:
{
  "name": "",
  "dob": "",
  "address": "",
  "pan": "",
  "aadhaar_last4": "",
  "annual_income_estimate": 0,
  "risk_flags": [],
  "kyc_status": "verified|flagged|incomplete"
}"""


async def analyze_kyc_documents(file_parts: list) -> dict:
    """Send uploaded KYC documents to Gemini for multimodal analysis."""
    try:
        model = _get_model()
        response = model.generate_content(
            [KYC_SYSTEM_PROMPT] + file_parts,
            generation_config=genai.types.GenerationConfig(
                temperature=0.1,
                max_output_tokens=1024,
            ),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except json.JSONDecodeError:
        logger.exception("Gemini KYC response was not valid JSON")
        return {
            "name": "",
            "dob": "",
            "address": "",
            "pan": "",
            "aadhaar_last4": "",
            "annual_income_estimate": 0,
            "risk_flags": ["parse_error"],
            "kyc_status": "incomplete",
        }
    except Exception:
        logger.exception("Gemini KYC analysis failed")
        return {
            "name": "",
            "dob": "",
            "address": "",
            "pan": "",
            "aadhaar_last4": "",
            "annual_income_estimate": 0,
            "risk_flags": ["api_error"],
            "kyc_status": "incomplete",
        }


def generate_risk_questionnaire(age: int, income_band: str) -> list[dict]:
    """Generate a 5-question risk profiling questionnaire calibrated to age and income."""
    try:
        model = _get_model()
        prompt = (
            f"Generate a 5-question investment risk profiling questionnaire for a client "
            f"aged {age} with an annual income band of {income_band}. "
            f"Each question should have 3 options mapped to Conservative (1), Moderate (2), "
            f"Aggressive (3). Return ONLY a JSON array: "
            f'[{{"question":"...","options":[{{"text":"...","score":1}},{{"text":"...","score":2}},{{"text":"...","score":3}}]}}]'
        )
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.3, max_output_tokens=2048),
        )
        text = response.text.strip()
        if text.startswith("```"):
            text = text.split("\n", 1)[1].rsplit("```", 1)[0].strip()
        return json.loads(text)
    except Exception:
        logger.exception("Failed to generate risk questionnaire")
        return [
            {
                "question": "How would you react to a 20% drop in your portfolio?",
                "options": [
                    {"text": "Sell everything immediately", "score": 1},
                    {"text": "Wait and watch for recovery", "score": 2},
                    {"text": "Buy more at lower prices", "score": 3},
                ],
            },
            {
                "question": "What is your primary investment objective?",
                "options": [
                    {"text": "Capital preservation", "score": 1},
                    {"text": "Balanced growth and income", "score": 2},
                    {"text": "Maximum capital appreciation", "score": 3},
                ],
            },
            {
                "question": "How long can you stay invested without needing the money?",
                "options": [
                    {"text": "Less than 3 years", "score": 1},
                    {"text": "3 to 7 years", "score": 2},
                    {"text": "More than 7 years", "score": 3},
                ],
            },
            {
                "question": "What portion of your savings are you investing?",
                "options": [
                    {"text": "Most of my savings", "score": 1},
                    {"text": "About half", "score": 2},
                    {"text": "A small portion I can afford to lose", "score": 3},
                ],
            },
            {
                "question": "Which portfolio mix appeals to you most?",
                "options": [
                    {"text": "80% debt, 20% equity", "score": 1},
                    {"text": "50% equity, 50% debt", "score": 2},
                    {"text": "80% equity, 20% debt", "score": 3},
                ],
            },
        ]


# ---------------------------------------------------------------------------
# Layer 2 — Portfolio Commentary (Streaming)
# ---------------------------------------------------------------------------

PORTFOLIO_COMMENTARY_PROMPT = """You are a senior private wealth advisor at an Indian private bank.
Write a personalized 3-paragraph monthly portfolio commentary.

Paragraph 1 — Performance: How did the portfolio perform vs the Nifty 50 benchmark
this month? What were the top 2 contributors and detractors? Be specific with numbers.

Paragraph 2 — Risk & Opportunity: What is the most important risk or opportunity
in the current allocation given the client's goals and risk profile?

Paragraph 3 — Action: Give ONE specific, actionable recommendation with clear
reasoning tied to the client's actual data and goals.

Rules:
- Address the client by first name
- Tone: warm, confident, jargon-free
- Never use generic filler — every sentence must reference actual data
- Do not use bullet points — flowing prose only

Client: {client_json}
Portfolio: {portfolio_json}
Market context: {market_summary}"""


async def stream_portfolio_commentary(
    client_json: str, portfolio_json: str, market_summary: str
) -> AsyncGenerator[str, None]:
    """Stream portfolio commentary token-by-token."""
    prompt = PORTFOLIO_COMMENTARY_PROMPT.format(
        client_json=client_json,
        portfolio_json=portfolio_json,
        market_summary=market_summary,
    )
    try:
        model = _get_model()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.7, max_output_tokens=2048),
            stream=True,
        )
        for chunk in response:
            if chunk.text:
                yield chunk.text
    except Exception:
        logger.exception("Gemini portfolio commentary streaming failed")
        yield "We're experiencing a temporary issue generating your portfolio commentary. Please try again shortly."


# ---------------------------------------------------------------------------
# Layer 3 — RM Copilot / Pre-call Brief
# ---------------------------------------------------------------------------

RM_COPILOT_PROMPT = """You are an intelligent copilot for a private banker at an Indian wealth management firm.
Generate a structured pre-call brief for the RM. Use exactly this format:

## Client Snapshot
2-sentence summary of the client's current financial situation and relationship status.

## Since Last Interaction
Bullet list of notable changes: large transactions, market moves affecting their holdings,
goal progress updates, any life events logged.

## Conversation Starters
3 specific, data-backed talking points the RM should raise. Each must reference actual numbers.

## Next Best Action
ONE specific product recommendation or action, with a single-sentence rationale
directly tied to the client's data, goals, and risk profile.

## Risk Flags
Any compliance, suitability, or relationship risks the RM must be aware of before the call.

Client data: {client_json}
Portfolio data: {portfolio_json}
Interaction history: {interaction_history_json}"""


async def generate_rm_brief(
    client_json: str, portfolio_json: str, interaction_history_json: str
) -> str:
    """Generate a structured pre-call brief for the RM."""
    prompt = RM_COPILOT_PROMPT.format(
        client_json=client_json,
        portfolio_json=portfolio_json,
        interaction_history_json=interaction_history_json,
    )
    try:
        model = _get_model()
        response = model.generate_content(
            prompt,
            generation_config=genai.types.GenerationConfig(temperature=0.5, max_output_tokens=2048),
        )
        return response.text
    except Exception:
        logger.exception("Gemini RM brief generation failed")
        return "Unable to generate the pre-call brief at this time. Please review client data manually."


async def rm_followup_chat(messages: list[dict]) -> str:
    """Continue a follow-up conversation about a specific client."""
    try:
        model = _get_model()
        chat = model.start_chat(history=[])
        for msg in messages[:-1]:
            role = "user" if msg["role"] == "user" else "model"
            chat.history.append({"role": role, "parts": [msg["content"]]})
        response = chat.send_message(messages[-1]["content"])
        return response.text
    except Exception:
        logger.exception("Gemini RM follow-up chat failed")
        return "I'm unable to respond right now. Please try again."


# ---------------------------------------------------------------------------
# Layer 4 — Voice (Aria) system prompt builder
# ---------------------------------------------------------------------------

def build_voice_system_prompt(
    client_name: str,
    segment: str,
    risk_profile: str,
    aum: float,
    return_pct: float,
    goals_summary: str,
    bank_name: str | None = None,
) -> str:
    """Build the system prompt for Aria voice assistant."""
    bank = bank_name or settings.BANK_NAME
    return f"""You are Aria, an intelligent wealth management voice assistant for {bank} Private Banking.
You are speaking with {client_name}, a {segment} client with a {risk_profile} risk profile.
Their portfolio is currently worth ₹{aum} crores with a {return_pct}% return this year.
Their primary financial goals are: {goals_summary}.

Behavioral guidelines:
- Speak in a warm, confident, and concise manner
- Never reveal full account numbers, passwords, or sensitive authentication data
- For portfolio questions, reference their actual holdings and performance figures
- Only recommend products suitable for their declared risk profile
- If asked something outside your scope, offer to connect them with their RM
- Keep all responses under 3 sentences unless the client explicitly asks for detail
- If the client sounds distressed or mentions a large loss, lead with empathy first"""
