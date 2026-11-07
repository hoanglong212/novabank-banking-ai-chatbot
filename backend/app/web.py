"""Serve only the compiled frontend, never the project directory."""
from pathlib import Path
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException
from starlette.responses import FileResponse


class SpaFiles(StaticFiles):
    async def get_response(self, path, scope):
        response = await self._response(path, scope)
        if response.media_type == 'text/html':
            # The shell names hashed bundles; a stale cached shell keeps running old JS after a rebuild.
            response.headers['Cache-Control'] = 'no-cache'
        return response

    async def _response(self, path, scope):
        normalized = path.replace('\\', '/').lstrip('/')
        try:
            return await super().get_response(path, scope)
        except HTTPException as exc:
            # A missing API or asset must never receive the application shell.
            if exc.status_code != 404 or normalized == 'api' or normalized.startswith(('api/', 'assets/')) or Path(normalized).suffix or any(p.startswith('.') for p in normalized.split('/')):
                raise
            return FileResponse(Path(self.directory) / 'index.html')


def mount_frontend(app: FastAPI, directory: str | Path):
    dist = Path(directory).resolve()
    if not (dist / 'index.html').is_file():
        raise RuntimeError('Frontend build missing. Run npm run build in frontend/.')
    # Register last so API routes retain their authentication and JSON responses.
    app.mount('/', SpaFiles(directory=dist, html=True), name='frontend')
