"""End-to-end auth flow against the real app and a test database."""


async def test_signup_returns_token_and_user(client, sample_user_data):
    response = await client.post("/api/auth/signup", json=sample_user_data)
    assert response.status_code == 201, response.text
    body = response.json()
    assert body["token_type"] == "bearer"
    assert body["access_token"]
    assert body["user"]["email"] == sample_user_data["email"]
    assert "hashed_password" not in body["user"]


async def test_signup_rejects_duplicate_email_case_insensitively(client, sample_user_data):
    assert (await client.post("/api/auth/signup", json=sample_user_data)).status_code == 201

    shouting = {**sample_user_data, "email": sample_user_data["email"].upper()}
    response = await client.post("/api/auth/signup", json=shouting)
    assert response.status_code == 409


async def test_signup_rejects_short_password(client, sample_user_data):
    response = await client.post("/api/auth/signup", json={**sample_user_data, "password": "short"})
    assert response.status_code == 422


async def test_login_with_json_credentials(client, sample_user_data):
    await client.post("/api/auth/signup", json=sample_user_data)

    response = await client.post(
        "/api/auth/login",
        json={"email": sample_user_data["email"], "password": sample_user_data["password"]},
    )
    assert response.status_code == 200, response.text
    assert response.json()["access_token"]


async def test_login_rejects_wrong_password(client, sample_user_data):
    await client.post("/api/auth/signup", json=sample_user_data)

    response = await client.post(
        "/api/auth/login",
        json={"email": sample_user_data["email"], "password": "not-the-password"},
    )
    assert response.status_code == 401


async def test_me_requires_a_token(client):
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_me_returns_the_signed_in_user(auth_client, sample_user_data):
    response = await auth_client.get("/api/auth/me")
    assert response.status_code == 200
    assert response.json()["full_name"] == sample_user_data["full_name"]


async def test_garbage_token_is_rejected(client):
    client.headers["Authorization"] = "Bearer not.a.real.token"
    assert (await client.get("/api/auth/me")).status_code == 401


async def test_health_endpoint(client):
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
