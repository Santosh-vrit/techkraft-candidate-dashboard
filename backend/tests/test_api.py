import pytest

from tests.conftest import admin_login, register_and_login

pytestmark = pytest.mark.asyncio


async def test_register_hardcodes_reviewer_role(client):
    resp = await client.post(
        "/auth/register",
        json={"email": "hacker@example.com", "password": "password123", "name": "Hacker", "role": "admin"},
    )
    assert resp.status_code == 201
    # even if a `role` key is smuggled into the JSON body, the response schema
    # has no such field and the server always assigns "reviewer"
    assert resp.json()["role"] == "reviewer"


async def test_create_and_fetch_candidate(client):
    admin_token = await admin_login(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = await client.post(
        "/candidates",
        json={
            "name": "Ada Lovelace",
            "email": "ada@example.com",
            "role_applied": "Backend Engineer",
            "skills": ["Python", "SQL"],
        },
        headers=headers,
    )
    assert create_resp.status_code == 201
    body = create_resp.json()
    assert body["name"] == "Ada Lovelace"
    assert body["status"] == "new"
    candidate_id = body["id"]

    get_resp = await client.get(f"/candidates/{candidate_id}", headers=headers)
    assert get_resp.status_code == 200
    assert get_resp.json()["email"] == "ada@example.com"

    list_resp = await client.get("/candidates", params={"skill": "Python"}, headers=headers)
    assert list_resp.status_code == 200
    listed = list_resp.json()
    assert listed["total"] == 1
    assert listed["items"][0]["id"] == candidate_id


async def test_candidate_soft_delete(client):
    admin_token = await admin_login(client)
    headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = await client.post(
        "/candidates",
        json={"name": "Grace Hopper", "email": "grace@example.com", "role_applied": "QA Engineer", "skills": []},
        headers=headers,
    )
    candidate_id = create_resp.json()["id"]

    del_resp = await client.delete(f"/candidates/{candidate_id}", headers=headers)
    assert del_resp.status_code == 204

    # soft-deleted candidates are excluded from lookups, but the row still exists
    get_resp = await client.get(f"/candidates/{candidate_id}", headers=headers)
    assert get_resp.status_code == 404


async def test_score_validation_rejects_out_of_range(client):
    admin_token = await admin_login(client)
    headers = {"Authorization": f"Bearer {admin_token}"}
    create_resp = await client.post(
        "/candidates",
        json={"name": "Linus T", "email": "linus@example.com", "role_applied": "Kernel Engineer", "skills": ["C"]},
        headers=headers,
    )
    candidate_id = create_resp.json()["id"]

    resp = await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Technical Skills", "score": 7, "note": "too high"},
        headers=headers,
    )
    assert resp.status_code == 422
