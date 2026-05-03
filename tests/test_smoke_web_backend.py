from __future__ import annotations

import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_socketio")

from lahso.web import create_app, socketio  # noqa: E402


def test_flask_backend_serves_index_and_default_config() -> None:
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    index_response = client.get("/")
    assert index_response.status_code == 200
    assert b"LAHSO - Learning Assisted Hybrid Simulation-Optimization" in (
        index_response.data
    )
    assert b"SvelteKit app under" in index_response.data
    assert b"bun --bun run dev" in index_response.data

    config_response = client.get("/api/config/default")
    assert config_response.status_code == 200
    config_payload = config_response.get_json()

    assert config_payload["success"] is True
    assert config_payload["config"]["num_simulations"] == 50000
    assert config_payload["default_files"]["network"] == "data/raw/network/Network.csv"


def test_socket_connection_gets_lahso_session() -> None:
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    flask_client = app.test_client()

    socket_client = socketio.test_client(app, flask_test_client=flask_client)

    assert socket_client.is_connected()
    received_events = socket_client.get_received()
    assert received_events[0]["name"] == "connected"
    assert received_events[0]["args"][0]["session_id"]
