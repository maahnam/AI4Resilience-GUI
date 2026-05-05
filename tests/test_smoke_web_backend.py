from __future__ import annotations

import pandas as pd
import pytest

pytest.importorskip("flask")
pytest.importorskip("flask_socketio")

from lahso.web import create_app, socketio  # noqa: E402
from lahso.web.jobs import BackgroundJobRunner  # noqa: E402
from lahso.web.state import SessionStore  # noqa: E402


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


def test_socket_can_join_api_session_room() -> None:
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    flask_client = app.test_client()
    socket_client = socketio.test_client(app, flask_test_client=flask_client)
    socket_client.get_received()

    session_id = "api-session-id"
    socket_client.emit("join_session", {"session_id": session_id})
    socketio.emit(
        "training_progress",
        {
            "session_id": session_id,
            "episode": 1,
            "total_episodes": 2,
            "data": [{"Episode": 1, "Total Cost": 10, "Total Reward": 5}],
        },
        room=session_id,
    )

    received_events = socket_client.get_received()
    assert received_events[0]["name"] == "training_progress"
    assert received_events[0]["args"][0]["session_id"] == session_id


def test_training_start_reports_active_session_for_frontend_reconnect() -> None:
    app = create_app({"TESTING": True, "SECRET_KEY": "test"})
    client = app.test_client()

    with client.session_transaction() as flask_session:
        flask_session["session_id"] = "active-training-session"

    session_store = app.config["LAHSO_SESSION_STORE"]
    lahso_session = session_store.get_or_create("active-training-session")
    lahso_session.training_active = True

    response = client.post("/api/training/start")
    payload = response.get_json()

    assert response.status_code == 200
    assert payload["success"] is False
    assert payload["error"] == "Training already active"
    assert payload["session_id"] == "active-training-session"


def test_training_worker_emits_immediate_and_episode_progress(monkeypatch) -> None:
    def fake_model_train(_config, _model_input):
        yield pd.DataFrame(
            [{"Episode": 1, "Total Cost": 123, "Total Reward": 45}]
        )

    import lahso.web.jobs as jobs_module

    monkeypatch.setattr(jobs_module, "model_train", fake_model_train)

    session_store = SessionStore()
    lahso_session = session_store.get_or_create("worker-session")
    lahso_session.training_active = True
    lahso_session.total_episodes = 1

    socketio_stub = RecordingSocketIO()
    BackgroundJobRunner().run_training(session_store, socketio_stub, "worker-session")

    progress_events = [
        event for event in socketio_stub.events if event["name"] == "training_progress"
    ]
    complete_events = [
        event for event in socketio_stub.events if event["name"] == "training_complete"
    ]

    assert progress_events[0]["payload"]["data"] == []
    assert progress_events[0]["payload"]["episode"] == 0
    assert progress_events[1]["payload"]["episode"] == 1
    assert progress_events[1]["payload"]["data"][0]["Total Cost"] == 123
    assert complete_events


class RecordingSocketIO:
    def __init__(self) -> None:
        self.events = []

    def emit(self, name, payload, room=None) -> None:
        self.events.append({"name": name, "payload": payload, "room": room})

    def sleep(self, _seconds) -> None:
        return None
