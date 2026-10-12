"""LLM categorization fallback: it must never raise and never invent a category."""

from unittest.mock import AsyncMock, patch

from app.config import settings
from app.services.categorization.llm import categorize_merchant_with_llm


def fake_groq(content: str):
    """A stand-in for AsyncGroq whose completion returns `content`."""
    choice = AsyncMock()
    choice.message.content = content

    completions = AsyncMock()
    completions.create.return_value = AsyncMock(choices=[choice])

    client = AsyncMock()
    client.chat.completions = completions
    return client, completions


async def test_llm_categorization_no_key():
    # With no API key the client is None, so the call short-circuits to "Other".
    with patch("app.services.categorization.llm.client", None):
        assert await categorize_merchant_with_llm("Unknown Merchant Inc.") == "Other"


async def test_llm_categorization_with_mocked_groq():
    client, completions = fake_groq('{"category": "Dining"}')

    with patch("app.services.categorization.llm.client", client):
        assert await categorize_merchant_with_llm("Chipotle Mexican Grill") == "Dining"

    completions.create.assert_called_once()
    kwargs = completions.create.call_args[1]
    # The model is configuration, not a literal: Groq retires model ids regularly.
    assert kwargs["model"] == settings.GROQ_CATEGORIZATION_MODEL
    assert kwargs["response_format"] == {"type": "json_object"}


async def test_llm_categorization_normalizes_casing():
    client, _ = fake_groq('{"category": "dining"}')

    with patch("app.services.categorization.llm.client", client):
        assert await categorize_merchant_with_llm("Chipotle") == "Dining"


async def test_llm_categorization_rejects_invented_category():
    client, _ = fake_groq('{"category": "Interstellar Travel"}')

    with patch("app.services.categorization.llm.client", client):
        assert await categorize_merchant_with_llm("SpaceX") == "Other"


async def test_llm_categorization_survives_provider_error():
    client, completions = fake_groq("{}")
    completions.create.side_effect = RuntimeError("503 Service Unavailable")

    with patch("app.services.categorization.llm.client", client):
        # A provider outage must degrade, not propagate -- writes depend on this.
        assert await categorize_merchant_with_llm("Anything") == "Other"


async def test_llm_categorization_skips_blank_merchant():
    client, completions = fake_groq('{"category": "Dining"}')

    with patch("app.services.categorization.llm.client", client):
        assert await categorize_merchant_with_llm("   ") == "Other"

    completions.create.assert_not_called()
