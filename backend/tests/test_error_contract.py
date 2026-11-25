async def test_unknown_route_uses_error_envelope(client):
    response = await client.get("/not-found")
    assert response.status_code == 404
    assert response.json()["error"]["code"] == "404"


async def test_method_error_uses_error_envelope(client):
    response = await client.put("/health")
    assert response.status_code == 405
    assert "error" in response.json()
