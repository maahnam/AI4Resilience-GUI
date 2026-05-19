from __future__ import annotations

from collections.abc import Mapping
from typing import Any

from flask import Flask, abort, jsonify, render_template, request, send_file
from flask_socketio import SocketIO
from jinja2 import TemplateNotFound

from lahso.web.jobs import BackgroundJobRunner
from lahso.web.services import (
    compare_result_files,
    compare_result_uploads,
    configure_implementation,
    configure_training,
    get_default_config_payload,
    validate_dataset,
)
from lahso.web.state import SessionStore


def register_routes(
    app: Flask,
    socketio: SocketIO,
    session_store: SessionStore,
    job_runner: BackgroundJobRunner,
) -> None:
    @app.route("/")
    def index():
        try:
            return render_template("index.html")
        except TemplateNotFound:
            return "HTML template not found. Please create templates/index.html", 404

    @app.route("/api/config/default", methods=["GET"])
    def get_default_config():
        try:
            return jsonify(get_default_config_payload())
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/session/status", methods=["GET"])
    def get_session_status():
        try:
            lahso_session = session_store.get_for_current_request()
            return jsonify({"success": True, **lahso_session.to_dict()})
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/artifacts/<path:artifact_id>", methods=["GET"])
    def download_artifact(artifact_id: str):
        lahso_session = session_store.get_for_current_request()
        artifact_path = lahso_session.artifact_path(artifact_id)
        if artifact_path is None or not artifact_path.exists():
            abort(404)
        return send_file(artifact_path, as_attachment=True)

    @app.route("/api/dataset/validate", methods=["POST"])
    def validate_dataset_route():
        try:
            lahso_session = session_store.get_for_current_request()
            return jsonify(
                validate_dataset(_request_payload(), lahso_session, request.files)
            )
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/training/configure", methods=["POST"])
    def configure_training_route():
        try:
            lahso_session = session_store.get_for_current_request()
            print(
                f"Configuring training for session {lahso_session.session_id}",
                flush=True,
            )
            return jsonify(
                configure_training(_request_payload(), lahso_session, request.files)
            )
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/training/start", methods=["POST"])
    def start_training():
        try:
            lahso_session = session_store.get_for_current_request()

            if lahso_session.training_active:
                return jsonify(
                    {
                        "success": False,
                        "error": "Training already active",
                        "session_id": lahso_session.session_id,
                    }
                )

            lahso_session.training_active = True
            lahso_session.training_paused = False
            lahso_session.current_episode = 0

            print(
                f"Starting training background job for session {lahso_session.session_id}",
                flush=True,
            )
            job_runner.start_training(session_store, socketio, lahso_session.session_id)

            return jsonify(
                {
                    "success": True,
                    "message": "Training started",
                    "session_id": lahso_session.session_id,
                }
            )
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/training/pause", methods=["POST"])
    def pause_training():
        try:
            lahso_session = session_store.get_for_current_request()
            if not lahso_session.training_active:
                return jsonify(
                    {"success": False, "error": "No training session active"}
                )

            lahso_session.training_paused = True

            return jsonify({"success": True, "message": "Training paused"})
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/training/resume", methods=["POST"])
    def resume_training():
        try:
            lahso_session = session_store.get_for_current_request()

            if not lahso_session.training_active:
                return jsonify(
                    {"success": False, "error": "No training session active"}
                )

            lahso_session.training_paused = False

            return jsonify({"success": True, "message": "Training resumed"})
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/training/stop", methods=["POST"])
    def stop_training():
        try:
            lahso_session = session_store.get_for_current_request()
            lahso_session.training_active = False
            lahso_session.training_paused = False

            return jsonify({"success": True, "message": "Training stopped"})
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/implementation/configure", methods=["POST"])
    def configure_implementation_route():
        try:
            lahso_session = session_store.get_for_current_request()
            return jsonify(
                configure_implementation(
                    _request_payload(),
                    lahso_session,
                    request.files,
                )
            )
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/implementation/execute", methods=["POST"])
    def execute_implementation():
        try:
            lahso_session = session_store.get_for_current_request()

            if lahso_session.simulation_active:
                return jsonify({"success": False, "error": "Simulation already active"})

            lahso_session.simulation_active = True

            print(
                f"Starting implementation background job for session {lahso_session.session_id}",
                flush=True,
            )
            job_runner.start_simulation(
                session_store,
                socketio,
                lahso_session.session_id,
            )

            return jsonify(
                {
                    "success": True,
                    "message": "Simulation started",
                    "session_id": lahso_session.session_id,
                }
            )
        except Exception as exc:
            return _json_error(exc)

    @app.route("/api/comparison/compare", methods=["POST"])
    def compare_results():
        try:
            if request.files or request.form:
                return jsonify(compare_result_uploads(request.form, request.files))
            return jsonify(compare_result_files(_json_payload()))
        except Exception as exc:
            return _json_error(exc)


def _request_payload() -> Mapping[str, Any]:
    return request.form if request.form else _json_payload()


def _json_payload() -> Mapping[str, Any]:
    return request.get_json(silent=True) or {}


def _json_error(exc: Exception):
    return jsonify({"success": False, "error": str(exc)}), 500
