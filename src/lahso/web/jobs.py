from __future__ import annotations

import time
from threading import Thread

from flask_socketio import SocketIO

from lahso.model_implementation import model_implementation
from lahso.model_train import model_train
from lahso.web.state import SessionStore


class BackgroundJobRunner:
    """Runs long LAHSO workflows away from request handlers."""

    def start_training(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> Thread:
        training_thread = Thread(
            target=self.run_training,
            args=(session_store, socketio, session_id),
            daemon=True,
        )
        training_thread.start()
        return training_thread

    def start_simulation(
        self,
        session_store: SessionStore,
        socketio: SocketIO,
        session_id: str,
    ) -> Thread:
        simulation_thread = Thread(
            target=self.run_simulation,
            args=(session_store, socketio, session_id),
            daemon=True,
        )
        simulation_thread.start()
        return simulation_thread

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
            training_gen = model_train(lahso_session.config, lahso_session.model_input)

            for result in training_gen:
                if not lahso_session.training_active:
                    break

                while lahso_session.training_paused:
                    time.sleep(1)
                    if not lahso_session.training_active:
                        break

                if result is not None:
                    if "Episode" in result.columns:
                        lahso_session.current_episode = result["Episode"].max()

                    socketio.emit(
                        "training_progress",
                        {
                            "session_id": session_id,
                            "episode": lahso_session.current_episode,
                            "total_episodes": lahso_session.total_episodes,
                            "data": (
                                result.to_dict("records")
                                if len(result) < 1000
                                else result.tail(100).to_dict("records")
                            ),
                        },
                        room=session_id,
                    )

                time.sleep(0.1)

            lahso_session.training_active = False
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
            simulation_gen = model_implementation(
                lahso_session.config,
                lahso_session.model_input,
            )

            for result in simulation_gen:
                if not lahso_session.simulation_active:
                    break

                if result is not None:
                    socketio.emit(
                        "simulation_progress",
                        {
                            "session_id": session_id,
                            "data": result.to_dict("records"),
                        },
                        room=session_id,
                    )

                time.sleep(0.5)

            lahso_session.simulation_active = False
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
            socketio.emit(
                "simulation_error",
                {"session_id": session_id, "error": str(exc)},
                room=session_id,
            )
