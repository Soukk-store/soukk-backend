from soukk_backend.settings.appSettings import settings


def preflight_headers(origin: str) -> dict:
    """What a browser sends before a cross-site POST with a JSON body."""
    return {
        "Origin": origin,
        "Access-Control-Request-Method": "POST",
        "Access-Control-Request-Headers": "authorization, content-type",
    }


async def test_frontend_is_allowed(client):
    response = await client.options("/auth/login", headers=preflight_headers(settings.frontend_url))

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == settings.frontend_url
    assert "access-control-allow-credentials" not in response.headers


async def test_other_websites_are_refused(client):
    response = await client.options("/auth/login", headers=preflight_headers("https://evil.example"))

    assert response.status_code == 400
    assert "access-control-allow-origin" not in response.headers


async def test_frontend_reads_normal_responses(client):
    response = await client.get("/health", headers={"Origin": settings.frontend_url})

    assert response.headers["access-control-allow-origin"] == settings.frontend_url


async def test_requests_without_origin_are_unaffected(client):
    """Mobile apps and servers send no Origin header; CORS doesn't apply to them."""
    response = await client.get("/health")

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers
