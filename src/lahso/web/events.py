from __future__ import annotations

from flask import session as flask_session
from flask_socketio import SocketIO, emit, join_room, leave_room

from lahso.web.state import SessionStore


def register_socket_events(socketio: SocketIO, session_store: SessionStore) -> None:
    @socketio.on("connect")
    def handle_connect():
        lahso_session = session_store.get_for_current_request()
        join_room(lahso_session.session_id)
        emit("connected", {"session_id": lahso_session.session_id})

    @socketio.on("disconnect")
    def handle_disconnect():
        session_id = flask_session.get("session_id")
        if session_id:
            leave_room(session_id)

    @socketio.on("join_session")
    def handle_join_session(data):
        session_id = data.get("session_id")
        if session_id:
            join_room(session_id)
