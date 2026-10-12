from datetime import date

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.database import get_db
from app.deps import get_current_user
from app.models.user import User
from app.schemas.chat import ChatRequest, ChatResponse, ChatStatus
from app.services.chat import answer_question

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.get("/status", response_model=ChatStatus)
async def chat_status(current_user: User = Depends(get_current_user)):
    """Report whether the assistant is configured, for the Settings page."""
    if not settings.groq_enabled:
        return ChatStatus(
            enabled=False,
            model=settings.GROQ_MODEL,
            detail="No GROQ_API_KEY configured. Add one to backend/.env and restart the API.",
        )
    return ChatStatus(
        enabled=True,
        model=settings.GROQ_MODEL,
        detail="Connected. Answers are grounded in your transaction data via tool calls.",
    )


@router.post("", response_model=ChatResponse)
async def send_message(
    payload: ChatRequest,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    """
    Answer a natural-language question about the user's finances.

    The heavy lifting is in `services.chat.answer_question`, which runs the Groq
    tool-use loop against the four read-only database tools.
    """
    try:
        return await answer_question(
            db,
            current_user,
            payload.message,
            payload.history,
            today=date.today().isoformat(),
        )
    except Exception as exc:  # noqa: BLE001 -- surface provider outages as 503, not 500
        raise HTTPException(
            status_code=status.HTTP_503_SERVICE_UNAVAILABLE,
            detail=f"The AI assistant is temporarily unavailable: {exc}",
        )
