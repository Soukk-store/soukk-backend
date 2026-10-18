from io import BytesIO

import pytest
from PIL import Image

from soukk_backend.core import storage
from soukk_backend.core.images import process_avatar
from soukk_backend.domains.users.userExceptions import InvalidImage
from soukk_backend.settings.appSettings import settings


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def make_image(
    fmt: str = "PNG", size: tuple[int, int] = (800, 600), mode: str = "RGB", color=0, **save
) -> bytes:
    out = BytesIO()
    Image.new(mode, size, color).save(out, fmt, **save)
    return out.getvalue()


@pytest.fixture(autouse=True)
def bucket(monkeypatch) -> dict[str, bytes]:
    """In-memory stand-in for R2, so no test talks to the real bucket."""
    objects: dict[str, bytes] = {}

    async def put(key: str, data: bytes, content_type: str) -> None:
        objects[key] = data

    async def delete(key: str) -> None:
        objects.pop(key, None)

    monkeypatch.setattr(storage, "put", put)
    monkeypatch.setattr(storage, "delete", delete)
    return objects


async def upload(client, token: str, data: bytes, filename: str = "me.png"):
    return await client.put(
        "/users/me/image", headers=bearer(token), files={"file": (filename, data)}
    )


def key_of(image_url: str) -> str:
    return image_url.removeprefix(settings.image_base_url.rstrip("/") + "/")


async def test_new_user_gets_default_image(client, logged_in):
    tokens = await logged_in()
    me = (await client.get("/auth/me", headers=bearer(tokens["access_token"]))).json()

    assert me["image_url"] == storage.public_url(settings.default_image_key)
    assert "image" not in me


async def test_upload_stores_square_webp(client, logged_in, bucket):
    tokens = await logged_in()
    response = await upload(client, tokens["access_token"], make_image())

    assert response.status_code == 200
    key = key_of(response.json()["image_url"])
    assert key.endswith(".webp")
    with Image.open(BytesIO(bucket[key])) as stored:
        assert stored.format == "WEBP"
        assert stored.size == (settings.image_size_px, settings.image_size_px)

    me = (await client.get("/auth/me", headers=bearer(tokens["access_token"]))).json()
    assert me["image_url"] == response.json()["image_url"]


async def test_new_upload_replaces_and_deletes_old_image(client, logged_in, bucket):
    tokens = await logged_in()
    first = key_of((await upload(client, tokens["access_token"], make_image())).json()["image_url"])
    second = key_of((await upload(client, tokens["access_token"], make_image("JPEG"))).json()["image_url"])

    assert first != second
    assert list(bucket) == [second]


async def test_non_image_is_rejected(client, logged_in, bucket):
    tokens = await logged_in()
    response = await upload(client, tokens["access_token"], b"<script>alert(1)</script>", "x.png")

    assert response.status_code == 422
    assert bucket == {}


async def test_unsupported_format_is_rejected(client, logged_in, bucket):
    tokens = await logged_in()
    response = await upload(client, tokens["access_token"], make_image("BMP"), "x.bmp")

    assert response.status_code == 422
    assert bucket == {}


async def test_oversized_upload_is_rejected(client, logged_in, bucket, monkeypatch):
    monkeypatch.setattr(settings, "image_max_bytes", 1000)
    tokens = await logged_in()
    response = await upload(client, tokens["access_token"], b"\0" * 1001)

    assert response.status_code == 413
    assert bucket == {}


async def test_delete_image_falls_back_to_default(client, logged_in, bucket):
    tokens = await logged_in()
    await upload(client, tokens["access_token"], make_image())

    response = await client.delete("/users/me/image", headers=bearer(tokens["access_token"]))

    assert response.status_code == 200
    assert response.json()["image_url"] == storage.public_url(settings.default_image_key)
    assert bucket == {}


async def test_image_endpoints_require_login(client):
    assert (await client.put("/users/me/image", files={"file": ("a.png", make_image())})).status_code == 401
    assert (await client.delete("/users/me/image")).status_code == 401


def test_process_avatar_drops_exif_and_keeps_transparency():
    exif = Image.Exif()
    exif[0x010F] = "SecretCam"  # Make
    jpeg = make_image("JPEG", exif=exif.tobytes())

    with Image.open(BytesIO(process_avatar(jpeg, 64))) as result:
        assert not result.getexif()

    png = make_image("PNG", mode="RGBA", color=(255, 0, 0, 0))
    with Image.open(BytesIO(process_avatar(png, 64))) as result:
        assert result.mode == "RGBA"
        assert result.size == (64, 64)


def test_process_avatar_rejects_decompression_bomb():
    huge = make_image("PNG", size=(8000, 6000), mode="1")
    with pytest.raises(InvalidImage):
        process_avatar(huge, 64)
