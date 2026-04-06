from fastapi import APIRouter, WebSocket

from .agent import run_agent

router = APIRouter()


@router.get("/")
async def health():
    return {"status": "ok", "service": "customer-support"}


@router.websocket("/ws")
async def websocket_endpoint(
    websocket: WebSocket,
    stt_language: str = "auto",
    llm_model: str = "gemini-2.5-flash",
):
    await run_agent(websocket, stt_language=stt_language, llm_model=llm_model)
