"""
The grounded chat assistant.

The whole point of this module is that the model is never trusted with numbers.
`answer_question` runs a tool-use loop: Groq decides which of the four read-only
database tools to call, the backend executes them against the signed-in user's
rows, and the results are fed back so the model can phrase an answer over real
data. If the model tries to answer a data question without calling a tool, the
request is retried with tool use forced.
"""

import json
import logging
from typing import Any, Optional

from groq import AsyncGroq
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models.category import CATEGORIES
from app.models.user import User
from app.schemas.chat import ChatMessage, ChatResponse, ToolCallRecord
from app.tools.definitions import TOOL_DEFINITIONS
from app.tools.executor import execute_tool

logger = logging.getLogger(__name__)

# Module-level client so the connection pool is shared; None disables the feature.
client: Optional[AsyncGroq] = (
    AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.groq_enabled else None
)

# Only the most recent turns are replayed. Long histories inflate token use and
# make the model more likely to answer from earlier text instead of fresh data.
MAX_HISTORY_TURNS = 8

NO_KEY_MESSAGE = (
    "The AI assistant is not configured yet. Add a free Groq API key as GROQ_API_KEY "
    "in backend/.env and restart the server. Your dashboard, transactions and budgets "
    "all work without it."
)

# Words that signal the user is asking about their actual figures. If the model
# returns an answer to one of these without having called a tool, that answer
# would be invented, so the request is retried with tool_choice="required".
_DATA_INTENT_TERMS = (
    "how much", "how many", "total", "spend", "spent", "spending", "budget", "left",
    "remaining", "income", "earn", "save", "saving", "savings", "balance", "average",
    "most", "least", "top", "biggest", "largest", "compare", "trend", "last month",
    "this month", "category", "categories", "transaction", "transactions", "over",
    "under", "rate", "summary", "breakdown", "merchant", "paid", "cost",
)


def _system_prompt(user: User, today: str) -> str:
    return (
        f"You are the AskYourWallet assistant, a personal finance analyst for {user.full_name}.\n"
        f"Today's date is {today}.\n\n"
        "HARD RULES\n"
        "1. Never state a number, amount, date or merchant from memory. Every figure you "
        "report must come from a tool result in this conversation. If you have not called "
        "a tool, call one.\n"
        "2. If a tool returns no data, say plainly that there is no data for that period. "
        "Never estimate, extrapolate or invent a plausible figure.\n"
        "3. Amounts in tool results are already in the user's currency. Report them as "
        "plain numbers with two decimals (e.g. 1,240.50). Do not add a currency symbol.\n"
        "4. Do not mention tools, functions, JSON or databases. Just answer.\n\n"
        "STYLE\n"
        "Be concise and specific: lead with the figure that answers the question, then at "
        "most two sentences of context. Use short bullet lists for breakdowns. Offer an "
        "observation or a concrete suggestion only when the data supports it.\n\n"
        f"Valid categories: {', '.join(CATEGORIES)}."
    )


def _summarize_result(name: str, result: dict[str, Any]) -> str:
    """One-line description of a tool result, shown in the UI as provenance."""
    if "error" in result:
        return f"lookup failed: {result['error']}"
    if name == "get_transactions":
        return f"{result.get('count', 0)} transactions, {result.get('total_amount', 0)} total"
    if name == "get_spending_by_category":
        categories = result.get("categories", [])
        return f"{len(categories)} categories in {result.get('month', '')}, {result.get('total_spent', 0)} spent"
    if name == "get_budget_status":
        budgets = result.get("budgets", [])
        if not budgets:
            return f"no budgets set for {result.get('month', '')}"
        return f"{len(budgets)} budgets, {result.get('over_budget_count', 0)} over limit"
    if name == "get_monthly_trend":
        return f"{result.get('months_returned', 0)} months of totals"
    return "completed"


def _suggested_actions(tool_names: list[str]) -> list[str]:
    """
    Follow-up prompts derived from what was just looked up.

    Deliberately deterministic -- asking the LLM to invent follow-ups would cost a
    second round trip and often produces questions the tools cannot answer.
    """
    if "get_budget_status" in tool_names:
        return [
            "Which budget am I closest to breaking?",
            "How does this month compare to last month?",
            "Where could I cut back to get under budget?",
        ]
    if "get_spending_by_category" in tool_names:
        return [
            "Show me the transactions behind my top category",
            "How does that compare to last month?",
            "Am I within budget on those categories?",
        ]
    if "get_monthly_trend" in tool_names:
        return [
            "Which category drove the change?",
            "What is my savings rate this month?",
            "Am I over budget anywhere?",
        ]
    if "get_transactions" in tool_names:
        return [
            "Group those by category",
            "What was my largest expense?",
            "How much did I spend in total last month?",
        ]
    return [
        "What did I spend the most on this month?",
        "Am I over budget anywhere?",
        "How has my spending changed over the last 6 months?",
    ]


def _looks_like_data_question(message: str) -> bool:
    lowered = message.lower()
    return any(term in lowered for term in _DATA_INTENT_TERMS)


def _build_messages(user: User, today: str, message: str, history: list[ChatMessage]) -> list[dict]:
    messages: list[dict] = [{"role": "system", "content": _system_prompt(user, today)}]
    for turn in history[-MAX_HISTORY_TURNS:]:
        messages.append({"role": turn.role, "content": turn.content})
    messages.append({"role": "user", "content": message})
    return messages


def _assistant_message_to_dict(message: Any) -> dict:
    """
    Convert the SDK's assistant message back into a plain dict.

    The tool-call ids must be echoed verbatim in the follow-up request, and doing
    this by hand (rather than passing the SDK object through) keeps the payload
    explicit and easy to test with mocks.
    """
    payload: dict[str, Any] = {"role": "assistant", "content": message.content or ""}
    if getattr(message, "tool_calls", None):
        payload["tool_calls"] = [
            {
                "id": call.id,
                "type": "function",
                "function": {
                    "name": call.function.name,
                    "arguments": call.function.arguments,
                },
            }
            for call in message.tool_calls
        ]
    return payload


async def answer_question(
    db: AsyncSession,
    user: User,
    message: str,
    history: list[ChatMessage],
    today: str,
) -> ChatResponse:
    """Answer a natural-language question by letting Groq drive the DB tools."""
    if client is None:
        return ChatResponse(
            response=NO_KEY_MESSAGE,
            suggested_actions=[],
            grounded=False,
        )

    messages = _build_messages(user, today, message, history)
    records: list[ToolCallRecord] = []
    final_text = ""

    # tool_choice starts as "auto" so simple conversational turns ("what can you
    # do?") do not force a pointless query.
    tool_choice: str = "auto"
    forced_retry_used = False

    for round_index in range(settings.GROQ_MAX_TOOL_ROUNDS):
        completion = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            tools=TOOL_DEFINITIONS,
            tool_choice=tool_choice,
            temperature=0.2,
            max_tokens=1024,
        )
        assistant_message = completion.choices[0].message
        requested_calls = getattr(assistant_message, "tool_calls", None) or []

        if not requested_calls:
            final_text = (assistant_message.content or "").strip()

            # The brief's hard rule: a question about the user's actual figures may
            # never be answered from the model's own guesswork. If it skipped the
            # tools, force one round of tool use and try again.
            if (
                not records
                and not forced_retry_used
                and _looks_like_data_question(message)
            ):
                forced_retry_used = True
                tool_choice = "required"
                continue
            break

        # Echo the assistant's tool request, then answer each call in turn.
        messages.append(_assistant_message_to_dict(assistant_message))
        # After the first round let the model decide again, otherwise "required"
        # would make it loop forever requesting tools.
        tool_choice = "auto"

        for call in requested_calls:
            name = call.function.name
            try:
                arguments = json.loads(call.function.arguments or "{}")
                if not isinstance(arguments, dict):
                    arguments = {}
            except json.JSONDecodeError:
                logger.warning("Model sent unparseable arguments for %s: %r", name, call.function.arguments)
                arguments = {}

            result = await execute_tool(name, arguments, db, user.id)
            records.append(
                ToolCallRecord(
                    name=name,
                    arguments=arguments,
                    summary=_summarize_result(name, result),
                )
            )
            messages.append({
                "role": "tool",
                "tool_call_id": call.id,
                "name": name,
                "content": json.dumps(result, default=str),
            })
    else:
        # Round budget exhausted while the model was still asking for tools. Ask
        # once more with tools withheld so it has to commit to an answer.
        logger.warning("Chat hit the %s-round tool limit", settings.GROQ_MAX_TOOL_ROUNDS)
        completion = await client.chat.completions.create(
            model=settings.GROQ_MODEL,
            messages=messages,
            temperature=0.2,
            max_tokens=1024,
        )
        final_text = (completion.choices[0].message.content or "").strip()

    if not final_text:
        final_text = (
            "I could not put together an answer for that. Try asking about a specific "
            "month, category or merchant."
        )

    return ChatResponse(
        response=final_text,
        tool_calls=records,
        suggested_actions=_suggested_actions([r.name for r in records]),
        grounded=bool(records),
    )
