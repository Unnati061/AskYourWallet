"""
Groq function-calling tool definitions.

These schemas are what the model sees. They are kept separate from the execution
layer in `executor.py` so the contract the LLM is shown and the code that runs
against the database can be reviewed independently.

Design notes:
  * Month arguments are "YYYY-MM" strings. Models handle ISO-ish date strings far
    more reliably than a pair of integer month/year fields.
  * Every description states that the data is the signed-in user's own, so the
    model never tries to pass a user id.
  * Every optional parameter is typed `["<type>", "null"]`. Nothing here is
    required, but models routinely fill an omitted argument in with an explicit
    `null` rather than leaving it out, and the provider validates tool calls
    against these schemas before we ever see them -- a bare `"type": "string"`
    turns that habit into a hard 400. The executor treats null and absent
    identically, so widening the schema costs nothing.
  * Amounts come back as plain numbers with a currency-free contract; formatting
    is the frontend's job.
"""

TOOL_DEFINITIONS = [
    {
        "type": "function",
        "function": {
            "name": "get_transactions",
            "description": (
                "Fetch the signed-in user's individual transactions with optional filters. "
                "Use this for questions about specific purchases, merchants, or date ranges "
                "(for example 'how much did I spend at Walmart in July', 'list my biggest "
                "expenses last week'). Returns at most 100 rows, newest first."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "start_date": {
                        "type": ["string", "null"],
                        "description": "Inclusive start date, YYYY-MM-DD.",
                    },
                    "end_date": {
                        "type": ["string", "null"],
                        "description": "Inclusive end date, YYYY-MM-DD.",
                    },
                    "category": {
                        "type": ["string", "null"],
                        "description": (
                            "Exact category name to filter by, e.g. 'Groceries', 'Dining', "
                            "'Transport', 'Housing', 'Utilities', 'Entertainment', 'Shopping', "
                            "'Healthcare', 'Education', 'Travel', 'Subscriptions', 'Insurance', "
                            "'Personal Care', 'Gifts & Donations', 'Income', 'Transfer', 'Other'."
                        ),
                    },
                    "type": {
                        "type": ["string", "null"],
                        "enum": ["income", "expense", None],
                        "description": "Restrict to money in or money out.",
                    },
                    "search": {
                        "type": ["string", "null"],
                        "description": "Case-insensitive text match on description, merchant or category.",
                    },
                    "limit": {
                        "type": ["integer", "null"],
                        "description": "Maximum rows to return (1-100, default 25).",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_spending_by_category",
            "description": (
                "Total the signed-in user's expenses for one month, grouped by category and "
                "sorted highest first. Use this for 'what did I spend most on', 'top expense "
                "category', or any breakdown-of-spending question."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": ["string", "null"],
                        "description": (
                            "Month to analyse as YYYY-MM. Omit for the current month."
                        ),
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_budget_status",
            "description": (
                "Compare the signed-in user's category budgets against what they actually spent "
                "in a month. Use this for any question about budgets, limits, whether they are "
                "over or under, or how much room is left."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "month": {
                        "type": ["string", "null"],
                        "description": "Month to check as YYYY-MM. Omit for the current month.",
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_monthly_trend",
            "description": (
                "Month-by-month totals of the signed-in user's income, expenses and net savings, "
                "oldest first. Use this for trends, comparisons between months, or questions "
                "about whether spending is rising or falling."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "months": {
                        "type": ["integer", "null"],
                        "description": "How many months back to include, 1-24 (default 6).",
                    },
                },
                "required": [],
            },
        },
    },
]

# Names the executor is allowed to dispatch, derived from the definitions above so
# the two can never drift apart.
TOOL_NAMES = frozenset(tool["function"]["name"] for tool in TOOL_DEFINITIONS)
