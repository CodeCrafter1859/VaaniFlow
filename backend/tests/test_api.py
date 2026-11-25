import pytest

from app.core.auth import consume_ticket


async def test_crud_and_owner_isolation(client):
    response = await client.post(
        "/api/v1/transcriptions", json={"title": "Meeting", "text": "नमस्ते hello"}
    )
    assert response.status_code == 201
    record = response.json()["data"]
    path = "/api/v1/transcriptions/" + record["id"]
    assert (await client.get(path)).json()["data"]["text"] == "नमस्ते hello"
    for method in ["get", "patch", "delete"]:
        kwargs = {"json": {"title": "Stolen"}} if method == "patch" else {}
        response = await getattr(client, method)(
            path, headers={"Authorization": "Bearer bob-token"}, **kwargs
        )
        assert response.status_code == 404
    assert (await client.patch(path, json={"title": "Updated"})).json()["data"][
        "title"
    ] == "Updated"
    assert (await client.delete(path)).status_code == 200
    assert (await client.get(path)).status_code == 404


async def test_search_pagination_stats(client):
    for title, lang, status in [
        ("Hindi", "hi", "completed"),
        ("English", "en", "failed"),
        ("100%", "en", "completed"),
    ]:
        await client.post(
            "/api/v1/transcriptions",
            json={"title": title, "language": lang, "status": status, "duration": 10},
        )
    result = (await client.get("/api/v1/transcriptions?page_size=1&sort=title&order=asc")).json()[
        "data"
    ]
    assert result["total"] == 3 and len(result["items"]) == 1
    assert (await client.get("/api/v1/transcriptions?search=%25")).json()["data"]["total"] == 1
    assert (await client.get("/api/v1/transcriptions?language=hi")).json()["data"]["total"] == 1
    assert (await client.get("/api/v1/transcriptions?status=failed")).json()["data"]["total"] == 1
    stats = (await client.get("/api/v1/dashboard/stats")).json()["data"]
    assert (stats["total"], stats["completed"], stats["failed"], stats["duration"]) == (3, 2, 1, 30)


@pytest.mark.parametrize(
    "body", [{"title": ""}, {"title": "x", "duration": -1}, {"title": "x", "owner_id": "other"}]
)
async def test_validation(client, body):
    response = await client.post("/api/v1/transcriptions", json=body)
    assert response.status_code == 422 and "error" in response.json()


async def test_unauthenticated_and_invalid_sort(client):
    assert (
        await client.get("/api/v1/transcriptions", headers={"Authorization": ""})
    ).status_code == 401
    assert (await client.get("/api/v1/transcriptions?sort=token_hash")).status_code == 422
    record = (await client.post("/api/v1/transcriptions", json={"title": "x"})).json()["data"]
    assert (
        await client.patch("/api/v1/transcriptions/" + record["id"], json={"title": None})
    ).status_code == 422


async def test_audio_rejects_invalid_content(client):
    assert (
        await client.post(
            "/api/v1/transcriptions/audio", files={"file": ("x.txt", b"text", "text/plain")}
        )
    ).status_code == 415
    assert (
        await client.post(
            "/api/v1/transcriptions/audio", files={"file": ("x.wav", b"bad", "audio/wav")}
        )
    ).status_code == 422


async def test_ticket_single_use_and_purpose(client, database):
    ticket = (await client.post("/api/v1/auth/ticket")).json()["data"]["ticket"]
    async with database() as db:
        from fastapi import HTTPException

        with pytest.raises(HTTPException):
            await consume_ticket(db, ticket, "upload")
        assert await consume_ticket(db, ticket, "websocket")
        with pytest.raises(HTTPException):
            await consume_ticket(db, ticket, "websocket")
