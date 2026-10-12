"""
Chat assistant tests.

Two halves: the tool executor (real queries, scoped to the signed-in user) and the
Groq tool-use loop, driven by a fake client so no network call or API key is needed.
The loop's contract is that a question about the user's own figures is never
answered without a tool call.
"""

import json
import uuid
from datetime import date
from types import SimpleNamespace
from unittest.mock import patch

import pytest

from app.config import settings
from app.tools.executor import execute_tool

TODAY = date.today()
CURRENT_MONTH = f"{TODAY.year}-{TODAY.month:02d}"


def this_month(day: int) -> str:
    return date(TODAY.year, TODAY.month, min(day, 28)).isoformat()


# --- Fake Groq client ---------------------------------------------------------


class FakeToolCall:
    def __init__(self, name: str, arguments: dict, call_id: str = "call_abc123"):
        self.id = call_id
        self.type = "function"
        self.function = SimpleNamespace(name=name, arguments=json.dumps(arguments))


class FakeMessage:
    def __init__(self, content: str | None = None, tool_calls: list | None = None):
        self.content = content
        self.tool_calls = tool_calls or []


class FakeCompletions:
    """Replays a scripted list of assistant messages and records every request."""

    def __init__(self, script: list[FakeMessage]):
        self.script = list(script)
        self.calls: list[dict] = []
        self.error: Exception | None = None

    async def create(self, **kwargs):
        if self.error:
            raise self.error
        # chat.py mutates and reuses one messages list, so snapshot it per call.
        self.calls.append({**kwargs, "messages": list(kwargs.get("messages", []))})
        message = self.script.pop(0) if self.script else FakeMessage(content="done")
        return SimpleNamespace(choices=[SimpleNamespace(message=message)])


class FakeGroq:
    def __init__(self, script: list[FakeMessage] | None = None):
        self.completions = FakeCompletions(script or [])
        self.chat = SimpleNamespace(completions=self.completions)


# --- Fixtures -----------------------------------------------------------------


@pytest.fixture
def enable_groq(monkeypatch):
    """Make settings report the assistant as configured without a real key."""
    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")


async def seed_month(auth_client) -> uuid.UUID:
    """Give the user one income and two expenses in the current month."""
    rows = [
        ("Payroll Direct Deposit", "3000.00", "income", "Income", 1),
        ("Whole Foods Market", "150.00", "expense", "Groceries", 4),
        ("Blue Bottle Coffee", "50.00", "expense", "Dining", 6),
    ]
    for description, amount, tx_type, category, day in rows:
        response = await auth_client.post(
            "/api/transactions",
            json={
                "date": this_month(day),
                "description": description,
                "amount": amount,
                "type": tx_type,
                "category": category,
            },
        )
        assert response.status_code == 201, response.text

    me = await auth_client.get("/api/auth/me")
    return uuid.UUID(me.json()["id"])


# --- Tool executor ------------------------------------------------------------


async def test_unknown_tool_returns_an_error_not_an_exception(auth_client, db_session):
    user_id = await seed_month(auth_client)
    result = await execute_tool("drop_all_tables", {}, db_session, user_id)
    assert "error" in result


async def test_get_spending_by_category_tool(auth_client, db_session):
    user_id = await seed_month(auth_client)

    result = await execute_tool(
        "get_spending_by_category", {"month": CURRENT_MONTH}, db_session, user_id
    )
    assert result["month"] == CURRENT_MONTH
    assert result["total_spent"] == 200.0
    assert [row["category"] for row in result["categories"]] == ["Groceries", "Dining"]
    assert result["categories"][0]["share_of_spending_pct"] == 75.0
    assert result["categories"][0]["transaction_count"] == 1


async def test_get_transactions_tool_filters_and_clamps(auth_client, db_session):
    user_id = await seed_month(auth_client)

    expenses = await execute_tool(
        "get_transactions", {"type": "expense", "limit": 500}, db_session, user_id
    )
    assert expenses["count"] == 2
    assert expenses["total_amount"] == 200.0
    # limit is clamped to MAX_ROWS, so a model asking for 500 cannot exhaust memory.
    assert expenses["truncated"] is False

    searched = await execute_tool(
        "get_transactions", {"search": "whole foods"}, db_session, user_id
    )
    assert searched["count"] == 1
    assert searched["transactions"][0]["category"] == "Groceries"

    windowed = await execute_tool(
        "get_transactions",
        {"start_date": this_month(5), "end_date": this_month(28)},
        db_session,
        user_id,
    )
    assert windowed["count"] == 1


async def test_get_budget_status_tool_with_and_without_budgets(auth_client, db_session):
    user_id = await seed_month(auth_client)

    empty = await execute_tool("get_budget_status", {"month": CURRENT_MONTH}, db_session, user_id)
    assert empty["budgets"] == []
    # The note exists so the model says "no budgets set" instead of inventing one.
    assert "not set any budgets" in empty["note"]

    await auth_client.put(
        "/api/budgets", json={"category": "Groceries", "monthly_limit": "100.00"}
    )
    filled = await execute_tool("get_budget_status", {"month": CURRENT_MONTH}, db_session, user_id)
    assert filled["over_budget_count"] == 1
    assert filled["budgets"][0] == {
        "category": "Groceries",
        "monthly_limit": 100.0,
        "spent": 150.0,
        "remaining": -50.0,
        "percent_used": 150.0,
        "over_budget": True,
    }


async def test_get_monthly_trend_tool_clamps_and_fills_gaps(auth_client, db_session):
    user_id = await seed_month(auth_client)

    result = await execute_tool("get_monthly_trend", {"months": 999}, db_session, user_id)
    assert result["months_returned"] == 24  # MAX_TREND_MONTHS
    assert result["trend"][-1]["month"] == CURRENT_MONTH
    assert result["trend"][-1]["income"] == 3000.0
    assert result["trend"][-1]["expenses"] == 200.0
    assert result["trend"][-1]["net"] == 2800.0
    # Empty months are still emitted so the model can describe a flat period.
    assert result["trend"][0]["expenses"] == 0.0

    default_window = await execute_tool("get_monthly_trend", {}, db_session, user_id)
    assert default_window["months_returned"] == 6


async def test_unparseable_month_falls_back_to_the_current_month(auth_client, db_session):
    user_id = await seed_month(auth_client)
    result = await execute_tool(
        "get_spending_by_category", {"month": "last August"}, db_session, user_id
    )
    assert result["month"] == CURRENT_MONTH


async def test_tools_cannot_read_another_users_rows(auth_client, client, db_session):
    await seed_month(auth_client)

    intruder = await client.post(
        "/api/auth/signup",
        json={"email": "snoop@example.com", "password": "password1234", "full_name": "Snoop"},
    )
    intruder_headers = {"Authorization": f"Bearer {intruder.json()['access_token']}"}
    intruder_id = uuid.UUID(
        (await client.get("/api/auth/me", headers=intruder_headers)).json()["id"]
    )

    # user_id is bound from the request, never from the model, so a hallucinated
    # id can only ever return that caller's own (empty) data.
    result = await execute_tool(
        "get_spending_by_category", {"month": CURRENT_MONTH}, db_session, intruder_id
    )
    assert result["total_spent"] == 0.0
    assert result["categories"] == []


# --- Chat endpoint ------------------------------------------------------------


async def test_chat_status_reports_configuration(auth_client, monkeypatch):
    monkeypatch.setattr(settings, "GROQ_API_KEY", "")
    disabled = await auth_client.get("/api/chat/status")
    assert disabled.status_code == 200
    assert disabled.json()["enabled"] is False
    assert "GROQ_API_KEY" in disabled.json()["detail"]

    monkeypatch.setattr(settings, "GROQ_API_KEY", "gsk_test_key")
    enabled = await auth_client.get("/api/chat/status")
    assert enabled.json()["enabled"] is True
    assert enabled.json()["model"] == settings.GROQ_MODEL


async def test_chat_without_a_key_explains_how_to_configure_it(auth_client):
    with patch("app.services.chat.client", None):
        response = await auth_client.post("/api/chat", json={"message": "How much did I spend?"})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["grounded"] is False
    assert body["tool_calls"] == []
    assert "GROQ_API_KEY" in body["response"]


async def test_chat_requires_authentication(client):
    assert (await client.post("/api/chat", json={"message": "hi"})).status_code == 401


async def test_chat_validates_the_message(auth_client):
    assert (await auth_client.post("/api/chat", json={"message": ""})).status_code == 422
    too_long = await auth_client.post("/api/chat", json={"message": "x" * 2001})
    assert too_long.status_code == 422


async def test_chat_reports_a_provider_outage_as_503(auth_client, enable_groq):
    fake = FakeGroq()
    fake.completions.error = RuntimeError("connection reset")

    with patch("app.services.chat.client", fake):
        response = await auth_client.post("/api/chat", json={"message": "hello"})
    # 503, not 500: the app is fine, the upstream provider is not.
    assert response.status_code == 503
    assert "temporarily unavailable" in response.json()["detail"]


async def test_chat_runs_the_tool_loop_and_answers_over_real_data(auth_client, enable_groq):
    await seed_month(auth_client)
    fake = FakeGroq([
        FakeMessage(tool_calls=[FakeToolCall("get_spending_by_category", {"month": CURRENT_MONTH})]),
        FakeMessage(content="You spent 200.00 this month, mostly on Groceries."),
    ])

    with patch("app.services.chat.client", fake):
        response = await auth_client.post(
            "/api/chat", json={"message": "How much did I spend this month?"}
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert body["grounded"] is True
    assert body["response"] == "You spent 200.00 this month, mostly on Groceries."
    assert body["tool_calls"][0]["name"] == "get_spending_by_category"
    assert body["tool_calls"][0]["arguments"] == {"month": CURRENT_MONTH}
    assert "200.0" in body["tool_calls"][0]["summary"]
    assert body["suggested_actions"]

    # The second request must carry the executed tool's real result back to Groq.
    follow_up = fake.completions.calls[1]["messages"]
    tool_messages = [m for m in follow_up if m.get("role") == "tool"]
    assert len(tool_messages) == 1
    assert tool_messages[0]["tool_call_id"] == "call_abc123"
    assert '"total_spent": 200.0' in tool_messages[0]["content"]


async def test_chat_forces_a_tool_call_when_the_model_tries_to_guess(auth_client, enable_groq):
    await seed_month(auth_client)
    fake = FakeGroq([
        FakeMessage(content="You probably spent around 800 on groceries."),
        FakeMessage(tool_calls=[FakeToolCall("get_spending_by_category", {"month": CURRENT_MONTH})]),
        FakeMessage(content="You spent 150.00 on Groceries."),
    ])

    with patch("app.services.chat.client", fake):
        response = await auth_client.post(
            "/api/chat", json={"message": "How much did I spend on groceries?"}
        )

    body = response.json()
    # The invented figure is discarded and never reaches the user.
    assert "probably" not in body["response"]
    assert body["response"] == "You spent 150.00 on Groceries."
    assert body["grounded"] is True

    choices = [call["tool_choice"] for call in fake.completions.calls]
    assert choices == ["auto", "required", "auto"]


async def test_chat_allows_a_plain_conversational_answer(auth_client, enable_groq):
    fake = FakeGroq([FakeMessage(content="I can break down your spending and budgets.")])

    with patch("app.services.chat.client", fake):
        response = await auth_client.post(
            "/api/chat", json={"message": "Hello, what can you do?"}
        )

    body = response.json()
    assert body["grounded"] is False
    assert body["tool_calls"] == []
    # A greeting is not a data question, so no pointless query is forced.
    assert len(fake.completions.calls) == 1
    assert fake.completions.calls[0]["tool_choice"] == "auto"


async def test_chat_replays_recent_history_and_the_system_prompt(auth_client, enable_groq):
    fake = FakeGroq([FakeMessage(content="Sure.")])

    with patch("app.services.chat.client", fake):
        await auth_client.post(
            "/api/chat",
            json={
                "message": "And the month before?",
                "history": [
                    {"role": "user", "content": "What did I spend in July?"},
                    {"role": "assistant", "content": "1,200.00."},
                ],
            },
        )

    messages = fake.completions.calls[0]["messages"]
    assert messages[0]["role"] == "system"
    assert "Never state a number" in messages[0]["content"]
    assert [m["content"] for m in messages[1:]] == [
        "What did I spend in July?",
        "1,200.00.",
        "And the month before?",
    ]


async def test_chat_gives_up_gracefully_when_the_model_never_stops_calling_tools(
    auth_client, enable_groq
):
    await seed_month(auth_client)
    rounds = settings.GROQ_MAX_TOOL_ROUNDS
    fake = FakeGroq([
        FakeMessage(tool_calls=[FakeToolCall("get_monthly_trend", {"months": 3}, f"call_{i}")])
        for i in range(rounds)
    ])

    with patch("app.services.chat.client", fake):
        response = await auth_client.post(
            "/api/chat", json={"message": "What is my spending trend?"}
        )

    assert response.status_code == 200, response.text
    body = response.json()
    assert len(body["tool_calls"]) == rounds
    # One final request with the tools withheld, so the model must commit to prose.
    assert len(fake.completions.calls) == rounds + 1
    assert "tools" not in fake.completions.calls[-1]
    assert body["response"] == "done"
