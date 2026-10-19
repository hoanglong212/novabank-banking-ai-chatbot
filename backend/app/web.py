"""Serve only the compiled frontend, never the project directory."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles


def mount_frontend(app: FastAPI, directory: str | Path):
    dist = Path(directory).resolve()
    if not (dist / 'index.html').is_file():
        raise RuntimeError('Frontend build missing. Run npm run build in frontend/.')
    # Register last so API routes retain their authentication and JSON responses.
    # This UI uses state-based navigation; unknown URLs should remain 404.
    app.mount('/', StaticFiles(directory=dist, html=True), name='frontend')
