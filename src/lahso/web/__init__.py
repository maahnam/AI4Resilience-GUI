"""Flask web backend for LAHSO."""

from typing import Any

__all__ = ["create_app", "socketio"]


def __getattr__(name: str) -> Any:
    if name in __all__:
        from lahso.web.factory import create_app, socketio

        return {
            "create_app": create_app,
            "socketio": socketio,
        }[name]
    raise AttributeError(name)
