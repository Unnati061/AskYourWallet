"""Budget upsert/status and dashboard aggregation over HTTP."""

from datetime import date

TODAY = date.today()
MONTH_PARAMS = {"month": TODAY.month, "year": TODAY.year}


def this_month(day: int) -> str:
    """A date string inside the current month, so it lands in the default window."""
    return date(TODAY.year, TODAY.month, min(day, 28)).isoformat()


async def add_expense(auth_client, amount: str, category: str, day: int = 5, **overrides):
    payload = {
        "date": this_month(day),
        "description": overrides.pop("description", f"{category} purchase"),
        "amount": amount,
        "type": "expense",
        "category": category,
    }
    payload.update(overrides)
    response = await auth_client.post("/api/transactions", json=payload)
    assert response.status_code == 201, response.text
    return response.json()


async def add_income(auth_client, amount: str, day: int = 1):
    response = await auth_client.post(
        "/api/transactions",
        json={
            "date": this_month(day),
            "description": "Payroll Direct Deposit",
            "amount": amount,
            "type": "income",
            "category": "Income",
        },
    )
    assert response.status_code == 201, response.text
    return response.json()


# --- Budgets -----------------------------------------------------------------


async def test_create_budget_rejects_unknown_category(auth_client):
    response = await auth_client.post(
        "/api/budgets", json={"category": "groceries", "monthly_limit": "400.00"}
    )
    # Lowercase is not canonical -- the UI must send names from /api/categories.
    assert response.status_code == 422


async def test_duplicate_budget_conflicts_but_put_upserts(auth_client):
    body = {"category": "Groceries", "monthly_limit": "400.00", **MONTH_PARAMS}

    assert (await auth_client.post("/api/budgets", json=body)).status_code == 201
    assert (await auth_client.post("/api/budgets", json=body)).status_code == 409

    # PUT is the idempotent form the UI uses, so re-submitting a category the user
    # already budgeted raises the limit instead of dead-ending on the 409.
    upserted = await auth_client.put(
        "/api/budgets", json={**body, "monthly_limit": "550.00"}
    )
    assert upserted.status_code == 200, upserted.text
    assert upserted.json()["monthly_limit"] == "550.00"

    listing = await auth_client.get("/api/budgets")
    assert len(listing.json()) == 1


async def test_budget_status_reports_spend_and_over_budget_flag(auth_client):
    await auth_client.put(
        "/api/budgets", json={"category": "Groceries", "monthly_limit": "200.00", **MONTH_PARAMS}
    )
    await auth_client.put(
        "/api/budgets", json={"category": "Dining", "monthly_limit": "100.00", **MONTH_PARAMS}
    )
    await add_expense(auth_client, "150.00", "Groceries")
    await add_expense(auth_client, "130.00", "Dining")

    response = await auth_client.get("/api/budgets/status", params=MONTH_PARAMS)
    assert response.status_code == 200, response.text
    statuses = {item["category"]: item for item in response.json()}

    groceries = statuses["Groceries"]
    assert groceries["actual_spent"] == "150.00"
    assert groceries["remaining"] == "50.00"
    assert groceries["percentage_used"] == 75.0
    assert groceries["is_over_budget"] is False
    # budget_id lets the UI edit or delete straight from the jar grid.
    assert groceries["budget_id"]

    dining = statuses["Dining"]
    assert dining["is_over_budget"] is True
    assert dining["percentage_used"] == 130.0
    assert dining["remaining"] == "-30.00"

    # Most-consumed first, so at-risk jars lead the grid.
    assert [item["category"] for item in response.json()] == ["Dining", "Groceries"]


async def test_recurring_budget_applies_to_every_month(auth_client):
    # month/year omitted => recurring
    await auth_client.put("/api/budgets", json={"category": "Housing", "monthly_limit": "1500.00"})

    for month, year in ((1, 2026), (7, 2026)):
        response = await auth_client.get(
            "/api/budgets/status", params={"month": month, "year": year}
        )
        categories = [item["category"] for item in response.json()]
        assert categories == ["Housing"], f"{month}/{year} -> {categories}"


async def test_period_budget_overrides_recurring_one(auth_client):
    await auth_client.put("/api/budgets", json={"category": "Housing", "monthly_limit": "1500.00"})
    await auth_client.put(
        "/api/budgets", json={"category": "Housing", "monthly_limit": "1800.00", **MONTH_PARAMS}
    )

    response = await auth_client.get("/api/budgets/status", params=MONTH_PARAMS)
    statuses = response.json()
    assert len(statuses) == 1
    assert statuses[0]["monthly_limit"] == "1800.00"


async def test_update_and_delete_budget(auth_client):
    created = (
        await auth_client.post(
            "/api/budgets", json={"category": "Dining", "monthly_limit": "100.00"}
        )
    ).json()

    edited = await auth_client.put(
        f"/api/budgets/{created['id']}", json={"monthly_limit": "175.00"}
    )
    assert edited.status_code == 200
    assert edited.json()["monthly_limit"] == "175.00"

    assert (await auth_client.delete(f"/api/budgets/{created['id']}")).status_code == 204
    assert (await auth_client.delete(f"/api/budgets/{created['id']}")).status_code == 404


async def test_budgets_are_scoped_to_their_owner(auth_client, client):
    created = (
        await auth_client.post(
            "/api/budgets", json={"category": "Dining", "monthly_limit": "100.00"}
        )
    ).json()

    intruder = await client.post(
        "/api/auth/signup",
        json={"email": "other@example.com", "password": "password1234", "full_name": "Other"},
    )
    headers = {"Authorization": f"Bearer {intruder.json()['access_token']}"}

    assert (await client.get("/api/budgets", headers=headers)).json() == []
    response = await client.delete(f"/api/budgets/{created['id']}", headers=headers)
    assert response.status_code == 404


# --- Dashboard ---------------------------------------------------------------


async def test_dashboard_summary_math(auth_client):
    await add_income(auth_client, "4000.00")
    await add_expense(auth_client, "1000.00", "Groceries", day=3)
    await add_expense(auth_client, "800.00", "Housing", day=4)

    response = await auth_client.get("/api/dashboard", params=MONTH_PARAMS)
    assert response.status_code == 200, response.text
    summary = response.json()["summary"]

    assert summary["total_income"] == "4000.00"
    assert summary["total_spent"] == "1800.00"
    assert summary["net_savings"] == "2200.00"
    # Already a percentage: 2200/4000 = 55%. The UI must not multiply by 100 again.
    assert summary["savings_rate"] == 55.0
    assert summary["transaction_count"] == 3
    assert summary["budget_health"] == "No budgets"


async def test_dashboard_savings_rate_is_zero_without_income(auth_client):
    await add_expense(auth_client, "50.00", "Dining")

    response = await auth_client.get("/api/dashboard", params=MONTH_PARAMS)
    assert response.json()["summary"]["savings_rate"] == 0.0


async def test_dashboard_budget_health_escalates(auth_client):
    await auth_client.put(
        "/api/budgets", json={"category": "Groceries", "monthly_limit": "100.00", **MONTH_PARAMS}
    )

    await add_expense(auth_client, "50.00", "Groceries", day=2)
    body = (await auth_client.get("/api/dashboard", params=MONTH_PARAMS)).json()
    assert body["summary"]["budget_health"] == "Good"

    await add_expense(auth_client, "35.00", "Groceries", day=3)  # 85% used
    body = (await auth_client.get("/api/dashboard", params=MONTH_PARAMS)).json()
    assert body["summary"]["budget_health"] == "Warning"

    await add_expense(auth_client, "40.00", "Groceries", day=4)  # 125% used
    body = (await auth_client.get("/api/dashboard", params=MONTH_PARAMS)).json()
    assert body["summary"]["budget_health"] == "Critical"


async def test_dashboard_breakdown_and_trend_shape(auth_client):
    await add_expense(auth_client, "300.00", "Groceries", day=2)
    await add_expense(auth_client, "100.00", "Dining", day=3)

    body = (await auth_client.get("/api/dashboard", params=MONTH_PARAMS)).json()

    breakdown = body["category_breakdown"]
    assert [item["category"] for item in breakdown] == ["Groceries", "Dining"]
    assert breakdown[0]["percentage"] == 75.0
    assert breakdown[0]["icon"]  # a Lucide icon name for the UI

    trend = body["monthly_trend"]
    assert len(trend) == 6
    assert trend[-1]["month"] == f"{TODAY.year}-{TODAY.month:02d}"
    assert trend[-1]["expenses"] == "400.00"
    assert trend[-1]["net"] == "-400.00"
    assert trend[-1]["label"]  # pre-formatted for the chart axis
    # Earlier months with no data are still present, so the line chart has no gaps.
    assert trend[0]["expenses"] == "0.00"

    assert len(body["recent_transactions"]) == 2
    assert body["budget_status"] == []


async def test_dashboard_rejects_impossible_month(auth_client):
    response = await auth_client.get("/api/dashboard", params={"month": 13, "year": 2026})
    assert response.status_code == 422


async def test_dashboard_requires_authentication(client):
    assert (await client.get("/api/dashboard")).status_code == 401
