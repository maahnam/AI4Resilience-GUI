from __future__ import annotations

import uuid
from dataclasses import dataclass, field
from threading import Lock
from typing import Any

from flask import session as flask_session

from lahso.config import Config


@dataclass
class LAHSOSession:
    session_id: str
    config: Config = field(default_factory=Config)
    model_input: Any | None = None
    training_generator: Any | None = None
    simulation_generator: Any | None = None
    training_active: bool = False
    simulation_active: bool = False
    training_paused: bool = False
    current_episode: int = 0
    total_episodes: int = 0

    def to_dict(self) -> dict[str, Any]:
        return {
            "session_id": self.session_id,
            "training_active": self.training_active,
            "simulation_active": self.simulation_active,
            "training_paused": self.training_paused,
            "current_episode": self.current_episode,
            "total_episodes": self.total_episodes,
        }


class SessionStore:
    """In-memory web session store.

    This deliberately keeps the current local behavior. Moving this behind a
    class gives us a single replacement point for Redis or database-backed
    job state later.
    """

    def __init__(self) -> None:
        self._sessions: dict[str, LAHSOSession] = {}
        self._lock = Lock()

    def get(self, session_id: str) -> LAHSOSession | None:
        return self._sessions.get(session_id)

    def get_or_create(self, session_id: str) -> LAHSOSession:
        with self._lock:
            if session_id not in self._sessions:
                self._sessions[session_id] = LAHSOSession(session_id)
            return self._sessions[session_id]

    def get_for_current_request(self) -> LAHSOSession:
        if "session_id" not in flask_session:
            flask_session["session_id"] = str(uuid.uuid4())

        return self.get_or_create(flask_session["session_id"])

    @property
    def active_sessions(self) -> dict[str, LAHSOSession]:
        return self._sessions
