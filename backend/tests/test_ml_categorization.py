"""Selective classification contract and integration with existing write paths."""
from unittest.mock import AsyncMock, patch

import numpy as np

from app.models.category import CATEGORIES
from app.services.categorization.ml import categorize_with_model, load_model, predict_probabilities
from app.services.transaction import parse_csv_statement, resolve_category


def test_artifact_is_fitted_and_rejects_blank_or_unseen_text():
    model = load_model()
    assert model is not None
    assert model["coef"].shape[0] == 16
    assert set(model["category_mapping"].values()) <= set(CATEGORIES)
    assert categorize_with_model("") is None
    assert categorize_with_model("zzzzunseen123") is None
    assert predict_probabilities("zzzzunseen123", model) is None
    assert categorize_with_model("hair cut") == "Personal Care"


def test_model_applies_threshold_and_rejects_ambiguous_source_labels():
    model = load_model()
    for label, probability, accepted in [("Health", .99, "Healthcare"), ("Health", .1, None), ("Food", .99, None)]:
        probs = np.zeros(len(model["classes"]))
        probs[model["classes"].index(label)] = probability
        with patch("app.services.categorization.ml.predict_probabilities", return_value=probs):
            assert categorize_with_model("a description") == accepted


async def test_manual_override_rules_income_and_model_precedence():
    with patch("app.services.transaction.categorize_with_model", return_value="Healthcare") as ml:
        assert await resolve_category("unknown", explicit_category="Other") == "Other"
        assert await resolve_category("Walmart") == "Groceries"
        assert await resolve_category("unknown credit", transaction_type="income") == "Income"
        ml.assert_not_called()
        assert await resolve_category("unknown expense") == "Healthcare"
        ml.assert_called_once()


async def test_abstention_preserves_llm_fallback():
    with patch("app.services.transaction.categorize_with_model", return_value=None), patch(
        "app.services.transaction.categorize_merchant_with_llm", new=AsyncMock(return_value="Shopping")
    ) as llm:
        assert await resolve_category("unrecognized merchant") == "Shopping"
        llm.assert_awaited_once()


def test_import_uses_model_only_for_unmatched_expenses():
    content = b"Date,Description,Amount\n2026-10-01,unknown expense,-100\n2026-10-02,unknown credit,200\n2026-10-03,Walmart,-30\n"
    with patch("app.services.transaction.categorize_with_model", return_value="Healthcare") as ml:
        rows = parse_csv_statement(content)
        assert [row["category"] for row in rows] == ["Healthcare", "Income", "Groceries"]
        ml.assert_called_once_with("unknown expense")


def test_model_can_be_disabled_and_missing_artifact_degrades():
    from app.config import settings
    with patch.object(settings, "ML_CATEGORIZATION_ENABLED", False):
        assert categorize_with_model("medicine") is None
    with patch("app.services.categorization.ml.load_model", return_value=None):
        assert categorize_with_model("medicine") is None


async def test_real_model_through_create_edit_and_csv_endpoints(auth_client):
    payload = {"date": "2026-10-01", "description": "hair cut", "amount": "100", "type": "expense"}
    created = await auth_client.post("/api/transactions", json=payload)
    assert created.status_code == 201, created.text
    assert created.json()["category"] == "Personal Care"
    changed = await auth_client.put(f"/api/transactions/{created.json()['id']}", json={"description": "mobile recharge"})
    assert changed.status_code == 200, changed.text
    assert changed.json()["category"] == "Subscriptions"
    imported = await auth_client.post("/api/transactions/import", files={"file": ("ml.csv", b"Date,Description,Amount\n2026-10-02,hair cut,-100\n", "text/csv")})
    assert imported.status_code == 201, imported.text
    rows = await auth_client.get("/api/transactions")
    assert any(row["description"] == "hair cut" and row["category"] == "Personal Care" for row in rows.json()["items"])


async def test_health_reports_loaded_model(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["ml_enabled"] is True
