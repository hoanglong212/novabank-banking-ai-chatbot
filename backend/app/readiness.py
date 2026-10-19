"""Lightweight model availability check; does not generate text or execute tools."""
import httpx
from fastapi.responses import JSONResponse
from .config import provider, setting


async def readiness():
    mode = provider()
    result = {'status': 'ready', 'llm_provider': mode}
    if mode == 'mock':
        return JSONResponse(result)
    model = setting('OLLAMA_MODEL', 'llama3.2:3b')
    result['model'] = model
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.post(
                setting('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/') + '/api/show',
                json={'model': model})
            response.raise_for_status()
            data = response.json()
            if not isinstance(data, dict) or not isinstance(data.get('details'), dict):
                raise ValueError('Invalid model metadata')
    except (httpx.HTTPError, ValueError, TypeError):
        result.update(status='not_ready', detail=f'Start Ollama and run: ollama pull {model}')
        return JSONResponse(result, status_code=503)
    return JSONResponse(result)
