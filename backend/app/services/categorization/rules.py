"""
Rule-based transaction categorization.

This is deliberately independent of the LLM fallback in `llm.py`: the rules
engine is pure, synchronous and offline, so it can be unit-tested and swapped
without touching the Groq integration. `categorize_by_rules` returns None when
nothing matches, which is the signal the caller uses to decide whether to spend
an LLM call.
"""

import re
from functools import lru_cache
from typing import Optional

# Default rule-based categorization mapping (lowercased keyword -> Category Name).
# Keys must be unique; where a merchant plausibly fits two categories the more
# common interpretation wins (e.g. Patreon is treated as a subscription).
DEFAULT_RULES: dict[str, str] = {
    # Groceries
    "walmart": "Groceries",
    "wal-mart": "Groceries",
    "target": "Groceries",
    "costco": "Groceries",
    "kroger": "Groceries",
    "aldi": "Groceries",
    "whole foods": "Groceries",
    "wholefoods": "Groceries",
    "safeway": "Groceries",
    "instacart": "Groceries",
    "trader joe": "Groceries",
    "grocery": "Groceries",
    "groceries": "Groceries",
    "supermarket": "Groceries",

    # Dining
    "mcdonald": "Dining",
    "starbucks": "Dining",
    "subway": "Dining",
    "burger king": "Dining",
    "dunkin": "Dining",
    "pizza": "Dining",
    "restaurant": "Dining",
    "cafe": "Dining",
    "coffee": "Dining",
    "bistro": "Dining",
    "pub": "Dining",
    "grill": "Dining",
    "uber eats": "Dining",
    "ubereats": "Dining",
    "grubhub": "Dining",
    "doordash": "Dining",
    "chipotle": "Dining",
    "taco bell": "Dining",

    # Transport
    "uber": "Transport",
    "lyft": "Transport",
    "shell": "Transport",
    "chevron": "Transport",
    "bp": "Transport",
    "exxon": "Transport",
    "gas station": "Transport",
    "fuel": "Transport",
    "transit": "Transport",
    "train": "Transport",
    "metro": "Transport",
    "parking": "Transport",
    "subway fare": "Transport",
    "amtrak": "Transport",
    "car wash": "Transport",

    # Housing
    "rent": "Housing",
    "rent payment": "Housing",
    "mortgage": "Housing",
    "landlord": "Housing",
    "apartment": "Housing",
    "leasing": "Housing",
    "hoa": "Housing",

    # Utilities
    "electric": "Utilities",
    "power": "Utilities",
    "water bill": "Utilities",
    "trash service": "Utilities",
    "cable tv": "Utilities",
    "internet": "Utilities",
    "comcast": "Utilities",
    "xfinity": "Utilities",
    "verizon": "Utilities",
    "at&t": "Utilities",
    "t-mobile": "Utilities",
    "metro pcs": "Utilities",
    "metropcs": "Utilities",
    "utility": "Utilities",
    "utilities": "Utilities",

    # Entertainment
    "netflix": "Entertainment",
    "spotify": "Entertainment",
    "hulu": "Entertainment",
    "disney": "Entertainment",
    "hbo": "Entertainment",
    "youtube": "Entertainment",
    "cinema": "Entertainment",
    "movie": "Entertainment",
    "theater": "Entertainment",
    "concert": "Entertainment",
    "ticketmaster": "Entertainment",
    "steam": "Entertainment",
    "nintendo": "Entertainment",
    "playstation": "Entertainment",
    "xbox": "Entertainment",

    # Shopping
    "amazon": "Shopping",
    "ebay": "Shopping",
    "nordstrom": "Shopping",
    "macy": "Shopping",
    "zara": "Shopping",
    "nike": "Shopping",
    "ikea": "Shopping",
    "best buy": "Shopping",
    "bestbuy": "Shopping",
    "apple store": "Shopping",
    "walmart.com": "Shopping",
    "target.com": "Shopping",

    # Healthcare
    "cvs": "Healthcare",
    "walgreens": "Healthcare",
    "pharmacy": "Healthcare",
    "doctor": "Healthcare",
    "dentist": "Healthcare",
    "dental": "Healthcare",
    "hospital": "Healthcare",
    "medical": "Healthcare",
    "clinic": "Healthcare",
    "prescription": "Healthcare",

    # Education
    "tuition": "Education",
    "university": "Education",
    "college": "Education",
    "textbook": "Education",
    "coursera": "Education",
    "udemy": "Education",

    # Travel
    "hotel": "Travel",
    "airbnb": "Travel",
    "flight": "Travel",
    "airline": "Travel",
    "airlines": "Travel",
    "delta air": "Travel",
    "united air": "Travel",
    "expedia": "Travel",
    "booking.com": "Travel",

    # Subscriptions
    "adobe": "Subscriptions",
    "microsoft": "Subscriptions",
    "google one": "Subscriptions",
    "icloud": "Subscriptions",
    "chatgpt": "Subscriptions",
    "patreon": "Subscriptions",
    "github": "Subscriptions",
    "saas": "Subscriptions",
    "subscription": "Subscriptions",

    # Insurance
    "geico": "Insurance",
    "progressive": "Insurance",
    "allstate": "Insurance",
    "state farm": "Insurance",
    "liberty mutual": "Insurance",
    "insurance": "Insurance",

    # Personal Care
    "salon": "Personal Care",
    "barber": "Personal Care",
    "spa": "Personal Care",
    "gym": "Personal Care",
    "fitness": "Personal Care",
    "haircut": "Personal Care",

    # Gifts & Donations
    "gofundme": "Gifts & Donations",
    "charity": "Gifts & Donations",
    "donation": "Gifts & Donations",
    "donations": "Gifts & Donations",
    "red cross": "Gifts & Donations",
    "gift": "Gifts & Donations",
    "gifts": "Gifts & Donations",

    # Income
    "payroll": "Income",
    "direct deposit": "Income",
    "salary": "Income",
    "paycheck": "Income",
    "dividend": "Income",
    "interest credit": "Income",
    "venmo cashout": "Income",
    "refund": "Income",

    # Transfer
    "transfer to": "Transfer",
    "transfer from": "Transfer",
    "atm withdrawal": "Transfer",
}

# Weak, descriptive keywords ("subscription", "coffee", "rent") as opposed to
# unambiguous merchant names ("netflix", "starbucks"). Generic keywords are only
# consulted after every brand rule has failed, otherwise a long generic word
# would outrank a short brand -- "Netflix.com Subscription" must resolve to
# Entertainment (the merchant), not Subscriptions (the noun).
GENERIC_KEYWORDS: frozenset[str] = frozenset({
    "grocery", "groceries", "supermarket",
    "pizza", "restaurant", "cafe", "coffee", "bistro", "pub", "grill",
    "gas station", "fuel", "transit", "train", "metro", "parking", "car wash",
    "rent", "rent payment", "mortgage", "landlord", "apartment", "leasing", "hoa",
    "electric", "power", "water bill", "trash service", "cable tv", "internet",
    "utility", "utilities",
    "cinema", "movie", "theater", "concert",
    "pharmacy", "doctor", "dentist", "dental", "hospital", "medical", "clinic",
    "prescription",
    "tuition", "university", "college", "textbook",
    "hotel", "flight", "airline", "airlines",
    "subscription", "saas",
    "insurance",
    "salon", "barber", "spa", "gym", "fitness", "haircut",
    "charity", "donation", "donations", "gift", "gifts",
    "payroll", "direct deposit", "salary", "paycheck", "dividend",
    "interest credit", "refund",
    "transfer to", "transfer from", "atm withdrawal",
})


def _rule_priority(keyword: str) -> tuple[int, int]:
    """Sort key: brand rules before generic ones, longest keyword first."""
    return (1 if keyword.lower() in GENERIC_KEYWORDS else 0, -len(keyword))


def _compile_rules(rules: tuple[tuple[str, str], ...]) -> list[tuple[re.Pattern[str], str]]:
    """
    Compile keyword rules into boundary-aware patterns in match-priority order.

    Two properties matter here:
      * Ordering makes the most specific rule win, so "subway fare" beats
        "subway", "target.com" beats "target", and any brand beats a generic noun.
      * The lookaround boundaries stop short keywords matching inside longer
        words -- "bp" must not match "bpay", "rent" must not match "rental car".
        \\b is not used because several keywords contain "." "&" or "-".
    """
    compiled: list[tuple[re.Pattern[str], str]] = []
    for keyword, category in sorted(rules, key=lambda kv: _rule_priority(kv[0])):
        pattern = re.compile(
            rf"(?<![a-z0-9]){re.escape(keyword.lower())}(?![a-z0-9])"
        )
        compiled.append((pattern, category))
    return compiled


@lru_cache(maxsize=8)
def _cached_compile(rules: tuple[tuple[str, str], ...]) -> tuple[tuple[re.Pattern[str], str], ...]:
    """Compiling ~180 patterns per CSV row would be wasteful, so memoize."""
    return tuple(_compile_rules(rules))


def categorize_by_rules(
    description: str, custom_rules: Optional[dict[str, str]] = None
) -> Optional[str]:
    """
    Categorize a transaction from keywords in its description.

    Custom rules take priority over the defaults so a user override always wins.
    Returns the canonical category name, or None when no rule matches -- the
    caller treats None as "ask the LLM".
    """
    if not description or not description.strip():
        return None

    haystack = description.lower()

    if custom_rules:
        for pattern, category in _cached_compile(tuple(custom_rules.items())):
            if pattern.search(haystack):
                return category

    for pattern, category in _cached_compile(tuple(DEFAULT_RULES.items())):
        if pattern.search(haystack):
            return category

    return None


# Bank statements pad merchant names with terminal ids, store numbers and
# processor prefixes. Stripping them gives the LLM (and the UI) a clean name.
_NOISE_PREFIXES = (
    "pos debit", "pos ", "ach debit", "ach credit", "ach ", "debit card purchase",
    "card purchase", "purchase authorized on", "recurring payment", "payment to",
    "sq *", "sq*", "tst*", "tst* ", "ppd id", "web id", "checkcard",
)
_NOISE_TOKEN = re.compile(r"[#*]?\d{3,}|x{2,}\d+|\b\d{2}/\d{2}\b", re.IGNORECASE)


def extract_merchant(description: str, max_length: int = 255) -> Optional[str]:
    """
    Derive a human-readable merchant name from a raw statement description.

    Example: "POS DEBIT SQ *BLUE BOTTLE COFFEE 4412 08/12" -> "BLUE BOTTLE COFFEE"
    """
    if not description or not description.strip():
        return None

    cleaned = description.strip()
    lowered = cleaned.lower()
    for prefix in _NOISE_PREFIXES:
        if lowered.startswith(prefix):
            cleaned = cleaned[len(prefix):].strip(" -*:")
            lowered = cleaned.lower()

    cleaned = _NOISE_TOKEN.sub("", cleaned)
    cleaned = re.sub(r"\s{2,}", " ", cleaned).strip(" -*:,.")

    if not cleaned:
        # Nothing survived the scrub -- fall back to the first word of the original.
        parts = description.split()
        cleaned = parts[0] if parts else ""

    return cleaned[:max_length] or None
