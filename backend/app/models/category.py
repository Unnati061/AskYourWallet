"""
Category is not a full ORM model -- categories are stored as strings on
transactions and budgets. This module holds the default category list and
icon mappings used by the rules engine and the frontend.
"""

# Canonical category names used throughout the app
CATEGORIES = [
    "Groceries",
    "Dining",
    "Transport",
    "Housing",
    "Utilities",
    "Entertainment",
    "Shopping",
    "Healthcare",
    "Education",
    "Travel",
    "Subscriptions",
    "Insurance",
    "Personal Care",
    "Gifts & Donations",
    "Income",
    "Transfer",
    "Other",
]

# Map category -> Lucide icon name (used by frontend)
CATEGORY_ICONS = {
    "Groceries": "shopping-cart",
    "Dining": "utensils",
    "Transport": "car",
    "Housing": "home",
    "Utilities": "zap",
    "Entertainment": "film",
    "Shopping": "shopping-bag",
    "Healthcare": "heart-pulse",
    "Education": "graduation-cap",
    "Travel": "plane",
    "Subscriptions": "repeat",
    "Insurance": "shield",
    "Personal Care": "scissors",
    "Gifts & Donations": "gift",
    "Income": "wallet",
    "Transfer": "arrow-left-right",
    "Other": "circle-dot",
}
