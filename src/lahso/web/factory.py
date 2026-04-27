from __future__ import annotations

import os

from dotenv import load_dotenv
from flask import Flask
from flask_socketio import SocketIO

from lahso.paths import (
    DEFAULT_GUROBI_LICENSE_FILE,
    Q_TABLES_DIR,
    TRAINING_METRICS_DIR,
    WEB_TEMPLATES_DIR,
    ensure_directories,
)
from lahso.web.events import register_socket_events
from lahso.web.jobs import BackgroundJobRunner
from lahso.web.routes import register_routes
from lahso.web.state import SessionStore

socketio = SocketIO()


def create_app(test_config: dict[str, object] | None = None) -> Flask:
    configure_environment()
    ensure_directories(
        WEB_TEMPLATES_DIR,
        Q_TABLES_DIR,
        TRAINING_METRICS_DIR,
    )

    app = Flask(__name__, template_folder=str(WEB_TEMPLATES_DIR))
    app.config.update(
        SECRET_KEY=os.getenv("LAHSO_SECRET_KEY", "lahso_dev_secret_key"),
    )
    if test_config is not None:
        app.config.update(test_config)

    session_store = SessionStore()
    job_runner = BackgroundJobRunner()
    app.config["LAHSO_SESSION_STORE"] = session_store
    app.config["LAHSO_JOB_RUNNER"] = job_runner

    socketio.init_app(app, cors_allowed_origins="*")
    register_routes(app, socketio, session_store, job_runner)
    register_socket_events(socketio, session_store)

    return app


def configure_environment() -> None:
    load_dotenv()
    if "GRB_LICENSE_FILE" not in os.environ and DEFAULT_GUROBI_LICENSE_FILE.exists():
        os.environ["GRB_LICENSE_FILE"] = str(DEFAULT_GUROBI_LICENSE_FILE)
