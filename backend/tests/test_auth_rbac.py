import pytest

from tests.conftest import admin_login, register_and_login

pytestmark = pytest.mark.asyncio


async def test_reviewer_cannot_see_another_reviewers_scores(client):
    admin_token = await admin_login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = await client.post(
        "/candidates",
        json={"name": "Ada Lovelace", "email": "ada2@example.com", "role_applied": "Backend Engineer", "skills": []},
        headers=admin_headers,
    )
    candidate_id = create_resp.json()["id"]

    token_a = await register_and_login(client, "reviewer-a@example.com")
    token_b = await register_and_login(client, "reviewer-b@example.com")
    headers_a = {"Authorization": f"Bearer {token_a}"}
    headers_b = {"Authorization": f"Bearer {token_b}"}

    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Technical Skills", "score": 4, "note": "solid"},
        headers=headers_a,
    )
    await client.post(
        f"/candidates/{candidate_id}/scores",
        json={"category": "Communication", "score": 5, "note": "great"},
        headers=headers_b,
    )

    detail_a = (await client.get(f"/candidates/{candidate_id}", headers=headers_a)).json()
    detail_b = (await client.get(f"/candidates/{candidate_id}", headers=headers_b)).json()

    assert len(detail_a["scores"]) == 1
    assert detail_a["scores"][0]["category"] == "Technical Skills"
    assert len(detail_b["scores"]) == 1
    assert detail_b["scores"][0]["category"] == "Communication"

    # admin sees both
    detail_admin = (await client.get(f"/candidates/{candidate_id}", headers=admin_headers)).json()
    assert len(detail_admin["scores"]) == 2


async def test_reviewer_cannot_see_internal_notes_or_create_candidates(client):
    admin_token = await admin_login(client)
    admin_headers = {"Authorization": f"Bearer {admin_token}"}

    create_resp = await client.post(
        "/candidates",
        json={
            "name": "Confidential Candidate",
            "email": "conf@example.com",
            "role_applied": "Engineer",
            "skills": [],
            "internal_notes": "Salary negotiation notes -- admin only",
        },
        headers=admin_headers,
    )
    candidate_id = create_resp.json()["id"]
    assert create_resp.json()["internal_notes"] == "Salary negotiation notes -- admin only"

    reviewer_token = await register_and_login(client, "reviewer-c@example.com")
    reviewer_headers = {"Authorization": f"Bearer {reviewer_token}"}

    detail = (await client.get(f"/candidates/{candidate_id}", headers=reviewer_headers)).json()
    assert detail["internal_notes"] is None

    # reviewers are not authorized to create candidates or edit notes
    forbidden_create = await client.post(
        "/candidates",
        json={"name": "X", "email": "x@example.com", "role_applied": "Y", "skills": []},
        headers=reviewer_headers,
    )
    assert forbidden_create.status_code == 403

    forbidden_notes = await client.patch(
        f"/candidates/{candidate_id}/notes",
        json={"internal_notes": "leaked"},
        headers=reviewer_headers,
    )
    assert forbidden_notes.status_code == 403


async def test_unauthenticated_request_rejected(client):
    resp = await client.get("/candidates")
    assert resp.status_code == 401
