"""Flask web backend for LAHSO."""

from lahso.web.factory import create_app, socketio

__all__ = ["create_app", "socketio"]
