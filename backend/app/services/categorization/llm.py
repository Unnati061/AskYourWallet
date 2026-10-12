"""
LLM fallback for categorization.

Kept deliberately separate from `rules.py`: the rules engine runs first and this
module is only reached for merchants no rule recognises. It never raises -- any
API problem degrades to "Other" so a transaction write is never blocked by the
AI provider being unavailable.
"""

import json
import logging
from typing import Optional

from groq import AsyncGroq

from app.config import settings
from app.models.category import CATEGORIES

logger = logging.getLogger(__name__)

# Module-level client so a single connection pool is reused; None when no API key
# is configured, which makes the whole LLM path a no-op.
client: Optional[AsyncGroq] = (
    AsyncGroq(api_key=settings.GROQ_API_KEY) if settings.groq_enabled else None
)

_SYSTEM_PROMPT = (
    "You are a transaction classifier for the AskYourWallet personal finance app.\n"
    "Given a merchant name or bank statement description, choose EXACTLY one "
    "category from this list:\n"
    f"[{', '.join(CATEGORIES)}]\n\n"
    'Respond with JSON only, in the form {"category": "<one category from the list>"}. '
    "No explanation, no extra keys."
)


async def categorize_merchant_with_llm(merchant_name: str) -> str:
    """
    Classify an unrecognised merchant into a canonical category via Groq.

    Returns "Other" on a missing key, a network error, or any response that is
    not one of the canonical categories.
    """
    if not client:
        logger.debug("Groq API key not set; skipping LLM categorization for %r", merchant_name)
        return "Other"
    if not merchant_name or not merchant_name.strip():
        return "Other"

    try:
        response = await client.chat.completions.create(
            messages=[
                {"role": "system", "content": _SYSTEM_PROMPT},
                {"role": "user", "content": f'Merchant: "{merchant_name}"'},
            ],
            model=settings.GROQ_CATEGORIZATION_MODEL,
            response_format={"type": "json_object"},
            temperature=0.0,
            max_tokens=64,
        )

        payload = json.loads(response.choices[0].message.content or "{}")
        suggested = payload.get("category")

        if suggested in CATEGORIES:
            return suggested

        # Second pass: the model may have altered the casing or spacing.
        normalized = str(suggested).strip().lower()
        for canonical in CATEGORIES:
            if canonical.lower() == normalized:
                return canonical

        logger.warning("Groq returned non-canonical category %r for %r", suggested, merchant_name)
    except Exception as exc:  # noqa: BLE001 -- categorization must never break a write
        logger.error("Groq categorization failed for %r: %s", merchant_name, exc)

    return "Other"
