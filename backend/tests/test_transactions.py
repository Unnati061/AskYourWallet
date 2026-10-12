from datetime import date
from decimal import Decimal
import pytest

from app.services.transaction import parse_csv_statement
from app.services.categorization.rules import categorize_by_rules


def test_categorize_by_rules():
    assert categorize_by_rules("Walmart Supercenter") == "Groceries"
    assert categorize_by_rules("Starbucks Coffee") == "Dining"
    assert categorize_by_rules("Uber Trip") == "Transport"
    assert categorize_by_rules("Netflix.com Subscription") == "Entertainment"
    assert categorize_by_rules("RANDOM MERCHANT NAME") is None


def test_parse_csv_statement_single_amount():
    csv_data = (
        "Date,Description,Amount\n"
        "2026-08-01,Walmart,$-50.00\n"
        "2026-08-02,Starbucks,-4.50\n"
        "2026-08-03,Payroll Credit,2500.00\n"
    ).encode("utf-8")

    parsed = parse_csv_statement(csv_data)
    assert len(parsed) == 3

    # Walmart Expense
    assert parsed[0]["description"] == "Walmart"
    assert parsed[0]["amount"] == Decimal("50.00")
    assert parsed[0]["type"] == "expense"
    assert parsed[0]["category"] == "Groceries"

    # Starbucks Expense
    assert parsed[1]["description"] == "Starbucks"
    assert parsed[1]["amount"] == Decimal("4.50")
    assert parsed[1]["type"] == "expense"
    assert parsed[1]["category"] == "Dining"

    # Payroll Credit Income
    assert parsed[2]["description"] == "Payroll Credit"
    assert parsed[2]["amount"] == Decimal("2500.00")
    assert parsed[2]["type"] == "income"
    assert parsed[2]["category"] == "Income"


def test_parse_csv_statement_debit_credit():
    csv_data = (
        "Transaction Date,Payee / Merchant,Debit,Credit\n"
        "08/10/2026,Chipotle,15.75,\n"
        "08/11/2026,Venmo Cashout,,120.00\n"
        "08/12/2026,Netflix,15.99,\n"
    ).encode("utf-8")

    parsed = parse_csv_statement(csv_data)
    assert len(parsed) == 3

    # Chipotle Expense
    assert parsed[0]["date"] == date(2026, 8, 10)
    assert parsed[0]["description"] == "Chipotle"
    assert parsed[0]["amount"] == Decimal("15.75")
    assert parsed[0]["type"] == "expense"
    assert parsed[0]["category"] == "Dining"

    # Venmo Credit
    assert parsed[1]["date"] == date(2026, 8, 11)
    assert parsed[1]["description"] == "Venmo Cashout"
    assert parsed[1]["amount"] == Decimal("120.00")
    assert parsed[1]["type"] == "income"
    assert parsed[1]["category"] == "Income"  # Venmo matches Income credit case

    # Netflix Expense
    assert parsed[2]["date"] == date(2026, 8, 12)
    assert parsed[2]["description"] == "Netflix"
    assert parsed[2]["amount"] == Decimal("15.99")
    assert parsed[2]["type"] == "expense"
    assert parsed[2]["category"] == "Entertainment"
