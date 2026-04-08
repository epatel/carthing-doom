import pytest


def test_serves_app_index(client):
    response = client.get("/test/")
    assert response.status_code == 200
    assert "Test App" in response.text


def test_serves_app_index_without_trailing_slash(client):
    response = client.get("/test")
    assert response.status_code in (200, 307)


def test_root_redirects_or_lists(client):
    response = client.get("/")
    assert response.status_code == 200


def test_missing_app_returns_404(client):
    response = client.get("/nonexistent/")
    assert response.status_code == 404


def test_websocket_echo(client):
    with client.websocket_connect("/ws") as ws:
        ws.send_json({"type": "ping", "data": {}})
        response = ws.receive_json()
        assert response["type"] == "pong"
