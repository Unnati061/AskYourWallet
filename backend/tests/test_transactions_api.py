"""Transaction CRUD, filtering, pagination and CSV import over HTTP."""

import io


def tx_payload(**overrides):
    payload = {
        "date": "2026-08-10",
        "description": "Whole Foods Market",
        "amount": "82.50",
        "type": "expense",
    }
    payload.update(overrides)
    return payload


async def test_create_transaction_auto_categorizes(auth_client):
    response = await auth_client.post("/api/transactions", json=tx_payload())
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["category"] == "Groceries"
    assert body["merchant"] == "Whole Foods Market"


async def test_create_transaction_honours_explicit_category(auth_client):
    response = await auth_client.post(
        "/api/transactions", json=tx_payload(category="Other")
    )
    assert response.status_code == 201
    # An explicit choice must survive -- it must not be silently reclassified.
    assert response.json()["category"] == "Other"


async def test_create_transaction_rejects_negative_amount(auth_client):
    response = await auth_client.post("/api/transactions", json=tx_payload(amount="-5.00"))
    assert response.status_code == 422


async def test_list_returns_pagination_envelope(auth_client):
    for day in range(1, 8):
        await auth_client.post(
            "/api/transactions", json=tx_payload(date=f"2026-08-{day:02d}")
        )

    response = await auth_client.get("/api/transactions", params={"page": 1, "size": 3})
    assert response.status_code == 200, response.text
    body = response.json()
    assert body["total"] == 7
    assert body["pages"] == 3
    assert body["page"] == 1
    assert len(body["items"]) == 3

    page_three = await auth_client.get("/api/transactions", params={"page": 3, "size": 3})
    assert len(page_three.json()["items"]) == 1


async def test_list_filters_by_type_category_and_search(auth_client):
    await auth_client.post("/api/transactions", json=tx_payload())
    await auth_client.post(
        "/api/transactions",
        json=tx_payload(description="Payroll Direct Deposit", amount="2400.00", type="income"),
    )

    only_income = await auth_client.get("/api/transactions", params={"type": "income"})
    assert only_income.json()["total"] == 1

    groceries = await auth_client.get("/api/transactions", params={"category": "Groceries"})
    assert groceries.json()["total"] == 1

    searched = await auth_client.get("/api/transactions", params={"search": "whole foods"})
    assert searched.json()["total"] == 1

    nothing = await auth_client.get("/api/transactions", params={"search": "zzzz"})
    assert nothing.json()["total"] == 0


async def test_list_rejects_invalid_type(auth_client):
    response = await auth_client.get("/api/transactions", params={"type": "banana"})
    assert response.status_code == 422


async def test_update_and_delete_transaction(auth_client):
    created = (await auth_client.post("/api/transactions", json=tx_payload())).json()

    updated = await auth_client.put(
        f"/api/transactions/{created['id']}",
        json={"amount": "99.99", "category": "Dining"},
    )
    assert updated.status_code == 200, updated.text
    assert updated.json()["amount"] == "99.99"
    assert updated.json()["category"] == "Dining"

    deleted = await auth_client.delete(f"/api/transactions/{created['id']}")
    assert deleted.status_code == 204

    assert (await auth_client.get(f"/api/transactions/{created['id']}")).status_code == 404


async def test_update_accepts_a_full_payload_including_date(auth_client):
    """The edit form resends every field, date included, so a partial-update
    schema that only tolerates omitted dates is not enough."""
    created = (await auth_client.post("/api/transactions", json=tx_payload())).json()

    updated = await auth_client.put(
        f"/api/transactions/{created['id']}",
        json={
            "date": "2026-08-15",
            "description": "Whole Foods Market",
            "amount": "15.00",
            "type": "expense",
            "category": "Groceries",
            "merchant": "Whole Foods Market",
            "notes": None,
        },
    )
    assert updated.status_code == 200, updated.text
    body = updated.json()
    assert body["date"] == "2026-08-15"
    assert body["amount"] == "15.00"


async def test_transactions_are_scoped_to_their_owner(auth_client, client):
    created = (await auth_client.post("/api/transactions", json=tx_payload())).json()

    other = await client.post(
        "/api/auth/signup",
        json={"email": "intruder@example.com", "password": "password1234", "full_name": "Nosy"},
    )
    intruder_token = other.json()["access_token"]

    response = await client.get(
        f"/api/transactions/{created['id']}",
        headers={"Authorization": f"Bearer {intruder_token}"},
    )
    assert response.status_code == 404


async def test_csv_import(auth_client):
    csv_bytes = (
        "Date,Description,Amount\n"
        "2026-08-01,Walmart Supercenter,-64.20\n"
        "2026-08-02,Starbucks,-5.75\n"
        "2026-08-03,Payroll Credit,2500.00\n"
    ).encode()

    response = await auth_client.post(
        "/api/transactions/import",
        files={"file": ("statement.csv", io.BytesIO(csv_bytes), "text/csv")},
    )
    assert response.status_code == 201, response.text
    assert response.json()["imported_count"] == 3

    listing = await auth_client.get("/api/transactions")
    assert listing.json()["total"] == 3


async def test_csv_import_rejects_non_csv(auth_client):
    response = await auth_client.post(
        "/api/transactions/import",
        files={"file": ("statement.pdf", io.BytesIO(b"%PDF"), "application/pdf")},
    )
    assert response.status_code == 400


async def test_csv_import_rejects_unrecognisable_columns(auth_client):
    response = await auth_client.post(
        "/api/transactions/import",
        files={"file": ("weird.csv", io.BytesIO(b"foo,bar\n1,2\n"), "text/csv")},
    )
    assert response.status_code == 400


async def test_categories_endpoint_lists_canonical_names(auth_client):
    response = await auth_client.get("/api/categories")
    assert response.status_code == 200
    names = [item["name"] for item in response.json()]
    assert "Groceries" in names
    assert "Gifts & Donations" in names
    assert all(item["icon"] for item in response.json())
