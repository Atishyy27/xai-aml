"""Deployment entrypoint.

Some hosts default their start command to `app:app`. This re-exports the real
FastAPI application so that both `app:app` and `backend.main:app` resolve to the
same object. It intentionally does no work of its own.

(The previous app.py mounted the app through Gradio, which pulled an uninstalled
`gradio` dependency and crashed on import. This does not.)
"""
from backend.main import app

__all__ = ["app"]
