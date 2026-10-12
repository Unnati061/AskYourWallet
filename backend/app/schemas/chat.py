from __future__ import annotations

from typing import Any, Literal, Optional

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """One turn of conversation history sent up from the client."""
    role: Literal["user", "assistant"]
    content: str


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    # Prior turns for context. Capped server-side to keep the prompt bounded.
    history: list[ChatMessage] = Field(default_factory=list)


class ToolCallRecord(BaseModel):
    """What the assistant looked up, surfaced in the UI so answers are auditable."""
    name: str
    arguments: dict[str, Any] = Field(default_factory=dict)
    # Short human-readable summary of the result, e.g. "12 transactions, 431.20 total"
    summary: str


class ChatResponse(BaseModel):
    response: str
    tool_calls: list[ToolCallRecord] = Field(default_factory=list)
    suggested_actions: list[str] = Field(default_factory=list)
    # False when the answer was produced without any database lookup, so the UI can
    # avoid implying the figures are grounded.
    grounded: bool = False


class ChatStatus(BaseModel):
    """Whether the AI assistant is usable, for the Settings page."""
    enabled: bool
    model: str
    detail: str
