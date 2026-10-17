import pytest
from fastapi import FastAPI, File, UploadFile
from httpx import ASGITransport, AsyncClient

from soukk_backend.core.bodySizeLimit import BodySizeLimitMiddleware
from soukk_backend.main import MULTIPART_OVERHEAD_BYTES
from soukk_backend.settings.appSettings import settings

LIMIT = 1000


@pytest.fixture
def received() -> list[int]:
    """Sizes of the uploads that reached the endpoint."""
    return []


@pytest.fixture
async def small_client(received):
    """A tiny app with a 1000 byte limit on PUT /upload only."""
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, limits={("PUT", "/upload"): LIMIT}, detail="Too big")

    @app.put("/upload")
    async def upload(file: UploadFile = File(...)):
        received.append(len(await file.read()))
        return {"ok": True}

    @app.post("/upload")
    async def other_method(file: UploadFile = File(...)):
        received.append(len(await file.read()))
        return {"ok": True}

    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as c:
        yield c


async def chunks(total: int, size: int = 256):
    """A body sent without Content-Length (chunked), as a client may do."""
    boundary = b"--b\r\nContent-Disposition: form-data; name=\"file\"; filename=\"a\"\r\n\r\n"
    yield boundary
    for _ in range(total // size):
        yield b"\0" * size
    yield b"\r\n--b--\r\n"


async def test_body_under_limit_reaches_endpoint(small_client, received):
    response = await small_client.put("/upload", files={"file": ("a", b"\0" * 500)})

    assert response.status_code == 200
    assert received == [500]


async def test_declared_oversized_body_is_refused_before_reading(small_client, received):
    response = await small_client.put("/upload", files={"file": ("a", b"\0" * 2000)})

    assert response.status_code == 413
    assert response.json() == {"detail": "Too big"}
    assert received == []


async def test_chunked_oversized_body_is_cut_off(small_client, received):
    response = await small_client.put(
        "/upload",
        content=chunks(4096),
        headers={"Content-Type": "multipart/form-data; boundary=b"},
    )

    assert "content-length" not in response.request.headers
    assert response.status_code == 413
    assert received == []


async def test_invalid_content_length_is_refused(small_client, received):
    response = await small_client.put(
        "/upload", content=b"x", headers={"Content-Length": "lots", "Content-Type": "text/plain"}
    )

    assert response.status_code == 400
    assert received == []


async def test_other_routes_are_not_limited(small_client, received):
    response = await small_client.post("/upload", files={"file": ("a", b"\0" * 2000)})

    assert response.status_code == 200
    assert received == [2000]


async def test_image_upload_route_is_limited_and_keeps_cors_headers(client):
    too_big = b"\0" * (settings.image_max_bytes + MULTIPART_OVERHEAD_BYTES + 1)
    response = await client.put(
        "/users/me/image",
        files={"file": ("me.png", too_big)},
        headers={"Origin": settings.frontend_url},
    )

    # Refused before authentication even runs: no token was sent.
    assert response.status_code == 413
    assert response.headers["access-control-allow-origin"] == settings.frontend_url
