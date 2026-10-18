import uuid

import pytest

from soukk_backend.domains.locations.locationService import MAX_LOCATIONS_PER_USER

URL = "/users/me/locations"


def bearer(token: str) -> dict:
    return {"Authorization": f"Bearer {token}"}


def location_body(**overrides) -> dict:
    return {
        "name": "Home",
        "district": "METN",
        "area": "JDEIDEH",
        "details": "Abou Khalil bldg, facing the pharmacy",
        "floor": "3",
        "latitude": 33.8901,
        "longitude": 35.5622,
        **overrides,
    }


@pytest.fixture
def account(client, logged_in):
    """Logged-in user: returns their auth headers and account phone."""

    async def _account(email: str = "user@example.com") -> dict:
        headers = bearer((await logged_in(email))["access_token"])
        me = (await client.get("/auth/me", headers=headers)).json()
        return {"headers": headers, "phone": me["phone"]}

    return _account


async def create(client, headers: dict, **overrides) -> dict:
    response = await client.post(URL, headers=headers, json=location_body(**overrides))
    assert response.status_code == 201, response.text
    return response.json()


async def list_locations(client, headers: dict) -> list[dict]:
    response = await client.get(URL, headers=headers)
    assert response.status_code == 200
    return response.json()


# --- CRUD and defaults ---


async def test_requires_login(client):
    assert (await client.get(URL)).status_code == 401
    assert (await client.post(URL, json=location_body())).status_code == 401


async def test_first_location_is_default(client, account):
    user = await account()
    assert await list_locations(client, user["headers"]) == []

    home = await create(client, user["headers"])
    mom = await create(client, user["headers"], name="Mom", district="KESERWAN", area="JOUNIEH")

    assert home["is_default"] is True
    assert mom["is_default"] is False
    assert home["district"] == "METN" and home["area"] == "JDEIDEH"
    assert home["latitude"] == 33.8901
    assert "user_id" not in home and "deleted_at" not in home


async def test_list_puts_default_first(client, account):
    user = await account()
    home = await create(client, user["headers"])
    mom = await create(client, user["headers"], name="Mom")

    response = await client.post(f"{URL}/{mom['id']}/default", headers=user["headers"])
    assert response.status_code == 200
    assert response.json()["is_default"] is True

    listed = await list_locations(client, user["headers"])
    assert [(loc["id"], loc["is_default"]) for loc in listed] == [(mom["id"], True), (home["id"], False)]


async def test_set_default_twice_is_harmless(client, account):
    user = await account()
    home = await create(client, user["headers"])

    response = await client.post(f"{URL}/{home['id']}/default", headers=user["headers"])

    assert response.status_code == 200
    assert response.json()["is_default"] is True


async def test_update_changes_only_sent_fields(client, account):
    user = await account()
    home = await create(client, user["headers"])

    response = await client.patch(
        f"{URL}/{home['id']}", headers=user["headers"], json={"floor": "Ground", "name": "  Flat  "}
    )

    assert response.status_code == 200
    updated = response.json()
    assert updated["floor"] == "Ground"
    assert updated["name"] == "Flat"
    assert updated["details"] == home["details"]
    assert updated["is_default"] is True


async def test_update_district_and_area_together(client, account):
    user = await account()
    home = await create(client, user["headers"])
    url = f"{URL}/{home['id']}"

    only_district = await client.patch(url, headers=user["headers"], json={"district": "KESERWAN"})
    assert only_district.status_code == 422

    both = await client.patch(
        url, headers=user["headers"], json={"district": "KESERWAN", "area": "JOUNIEH"}
    )
    assert both.status_code == 200
    assert both.json()["district"] == "KESERWAN"


async def test_update_cannot_clear_required_fields(client, account):
    user = await account()
    home = await create(client, user["headers"])

    response = await client.patch(f"{URL}/{home['id']}", headers=user["headers"], json={"name": None})

    assert response.status_code == 422


async def test_delete_hides_location(client, account):
    user = await account()
    home = await create(client, user["headers"])
    mom = await create(client, user["headers"], name="Mom")

    response = await client.delete(f"{URL}/{mom['id']}", headers=user["headers"])

    assert response.status_code == 204
    assert [loc["id"] for loc in await list_locations(client, user["headers"])] == [home["id"]]
    # Soft-deleted rows are invisible everywhere, including set-default and update.
    assert (await client.post(f"{URL}/{mom['id']}/default", headers=user["headers"])).status_code == 404
    assert (await client.patch(f"{URL}/{mom['id']}", headers=user["headers"], json={"floor": "1"})).status_code == 404
    assert (await client.delete(f"{URL}/{mom['id']}", headers=user["headers"])).status_code == 404


async def test_deleting_default_promotes_most_recent(client, account):
    user = await account()
    home = await create(client, user["headers"])
    await create(client, user["headers"], name="Work")
    mom = await create(client, user["headers"], name="Mom")

    await client.delete(f"{URL}/{home['id']}", headers=user["headers"])

    listed = await list_locations(client, user["headers"])
    assert listed[0]["id"] == mom["id"]
    assert [loc["is_default"] for loc in listed] == [True, False]


async def test_deleting_last_location_leaves_no_default(client, account):
    user = await account()
    home = await create(client, user["headers"])

    await client.delete(f"{URL}/{home['id']}", headers=user["headers"])
    new = await create(client, user["headers"], name="New")

    assert new["is_default"] is True


async def test_location_limit(client, account):
    user = await account()
    for i in range(MAX_LOCATIONS_PER_USER):
        await create(client, user["headers"], name=f"Place {i}")

    response = await client.post(URL, headers=user["headers"], json=location_body())

    assert response.status_code == 409
    assert len(await list_locations(client, user["headers"])) == MAX_LOCATIONS_PER_USER


# --- Ownership ---


async def test_other_users_location_is_not_found(client, account):
    alice = await account("alice@example.com")
    bob = await account("bob@example.com")
    alice_home = await create(client, alice["headers"])
    bob_home = await create(client, bob["headers"])
    url = f"{URL}/{bob_home['id']}"

    assert (await client.post(f"{url}/default", headers=alice["headers"])).status_code == 404
    assert (await client.patch(url, headers=alice["headers"], json={"floor": "9"})).status_code == 404
    assert (await client.delete(url, headers=alice["headers"])).status_code == 404

    # Nothing changed on either side.
    assert await list_locations(client, bob["headers"]) == [bob_home]
    assert await list_locations(client, alice["headers"]) == [alice_home]


async def test_unknown_id_is_not_found(client, account):
    user = await account()

    response = await client.patch(f"{URL}/{uuid.uuid4()}", headers=user["headers"], json={"floor": "1"})

    assert response.status_code == 404


@pytest.mark.parametrize("field", ["user_id", "is_default", "id", "deleted_at"])
async def test_server_owned_fields_are_rejected(client, account, field):
    user = await account()
    value = str(uuid.uuid4()) if field in {"user_id", "id"} else True

    response = await client.post(URL, headers=user["headers"], json=location_body(**{field: value}))

    assert response.status_code == 422
    assert await list_locations(client, user["headers"]) == []


async def test_update_rejects_server_owned_fields(client, account):
    user = await account()
    home = await create(client, user["headers"])
    await create(client, user["headers"], name="Mom")

    response = await client.patch(f"{URL}/{home['id']}", headers=user["headers"], json={"is_default": False})

    assert response.status_code == 422


# --- Validation ---


@pytest.mark.parametrize(
    "overrides",
    [
        {"district": "PARIS"},
        {"district": "METN", "area": "JOUNIEH"},  # Jounieh is in Keserwan
        {"area": "NOWHERE"},
        {"latitude": 48.85},
        {"longitude": 2.35},
        {"latitude": 0, "longitude": 0},
        {"name": "   "},
        {"floor": ""},
        {"details": "x" * 501},
    ],
)
async def test_invalid_location_is_rejected(client, account, overrides):
    user = await account()

    response = await client.post(URL, headers=user["headers"], json=location_body(**overrides))

    assert response.status_code == 422


async def test_coordinates_are_rounded(client, account):
    user = await account()

    home = await create(client, user["headers"], latitude=33.890123456, longitude=35.562298765)

    assert home["latitude"] == 33.890123
    assert home["longitude"] == 35.562299


# --- Receiver phone ---


async def test_receiver_phone_defaults_to_account_phone(client, account):
    user = await account()

    home = await create(client, user["headers"])

    assert home["receiver_phone"] == user["phone"]


async def test_receiver_phone_is_normalized_like_registration(client, account):
    user = await account()

    mom = await create(client, user["headers"], receiver_phone="03 123-456")

    assert mom["receiver_phone"] == "+9613123456"


async def test_invalid_receiver_phone_is_rejected(client, account):
    user = await account()

    response = await client.post(URL, headers=user["headers"], json=location_body(receiver_phone="12345"))

    assert response.status_code == 422


async def test_receiver_phone_can_change_and_revert(client, account):
    user = await account()
    mom = await create(client, user["headers"], receiver_phone="03 123 456")
    url = f"{URL}/{mom['id']}"

    changed = await client.patch(url, headers=user["headers"], json={"receiver_phone": "70 987 654"})
    assert changed.json()["receiver_phone"] == "+96170987654"

    untouched = await client.patch(url, headers=user["headers"], json={"floor": "2"})
    assert untouched.json()["receiver_phone"] == "+96170987654"

    reverted = await client.patch(url, headers=user["headers"], json={"receiver_phone": None})
    assert reverted.status_code == 200
    assert reverted.json()["receiver_phone"] == user["phone"]
