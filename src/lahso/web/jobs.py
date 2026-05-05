from __future__ import annotations

from typing import Any

from flask_socketio import SocketIO

from lahso.model_implementation import model_implementation
from lahso.model_train import model_train
from lahso.web.serialization import dataframe_records, json_safe
from lahso.web.state import SessionStore


class BackgroundJobRunner:
    """Runs long LAHSO workflows away from request handlers."""

    def start_training(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> Any:
        return socketio.start_background_task(
            self.run_training,
            session_store,
            socketio,
            session_id,
        )

    def start_simulation(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> Any:
        return socketio.start_background_task(
            self.run_simulation,
            session_store,
            socketio,
            session_id,
        )

    def run_training(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> None:
        lahso_session = session_store.get(session_id)
        if lahso_session is None:
            return

        try:
            print(f"Training worker started for session {session_id}", flush=True)
            socketio.emit(
                "training_progress",
                {
                    "session_id": session_id,
                    "episode": lahso_session.current_episode,
                    "total_episodes": lahso_session.total_episodes,
                    "data": [],
                },
                room=session_id,
            )
            socketio.sleep(0)
            training_gen = model_train(lahso_session.config, lahso_session.model_input)

            for result in training_gen:
                if not lahso_session.training_active:
                    break

                while lahso_session.training_paused:
                    socketio.sleep(1)
                    if not lahso_session.training_active:
                        break

                if result is not None:
                    if "Episode" in result.columns:
                        lahso_session.current_episode = json_safe(
                            result["Episode"].max()
                        )

                    print(
                        "Training worker emitting episode "
                        f"{lahso_session.current_episode}/"
                        f"{lahso_session.total_episodes} for session {session_id}",
                        flush=True,
                    )
                    socketio.emit(
                        "training_progress",
                        {
                            "session_id": session_id,
                            "episode": lahso_session.current_episode,
                            "total_episodes": lahso_session.total_episodes,
                            "data": dataframe_records(result, limit=100),
                        },
                        room=session_id,
                    )

                socketio.sleep(0.1)

            lahso_session.training_active = False
            print(f"Training worker completed for session {session_id}", flush=True)
            socketio.emit(
                "training_complete",
                {
                    "session_id": session_id,
                    "message": "Training completed successfully",
                },
                room=session_id,
            )

        except Exception as exc:
            lahso_session.training_active = False
            print(
                f"Training worker failed for session {session_id}: {exc}",
                flush=True,
            )
            socketio.emit(
                "training_error",
                {"session_id": session_id, "error": str(exc)},
                room=session_id,
            )

    def run_simulation(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> None:
        lahso_session = session_store.get(session_id)
        if lahso_session is None:
            return

        try:
            print(f"Implementation worker started for session {session_id}", flush=True)
            socketio.emit(
                "simulation_progress",
                {
                    "session_id": session_id,
                    "data": [],
                },
                room=session_id,
            )
            socketio.sleep(0)
            simulation_gen = model_implementation(
                lahso_session.config,
                lahso_session.model_input,
            )

            for result in simulation_gen:
                if not lahso_session.simulation_active:
                    break

                if result is not None:
                    print(
                        f"Implementation worker emitting progress for session {session_id}",
                        flush=True,
                    )
                    socketio.emit(
                        "simulation_progress",
                        {
                            "session_id": session_id,
                            "data": dataframe_records(result),
                        },
                        room=session_id,
                    )

                socketio.sleep(0.5)

            lahso_session.simulation_active = False
            print(f"Implementation worker completed for session {session_id}", flush=True)
            socketio.emit(
                "simulation_complete",
                {
                    "session_id": session_id,
                    "message": "Simulation completed successfully",
                },
                room=session_id,
            )

        except Exception as exc:
            lahso_session.simulation_active = False
            print(
                f"Implementation worker failed for session {session_id}: {exc}",
                flush=True,
            )
            socketio.emit(
                "simulation_error",
                {"session_id": session_id, "error": str(exc)},
                room=session_id,
            )
