"""Agent package. Legacy public symbols are loaded lazily to avoid DB cycles."""
def __getattr__(name):
    if name in ('MockAgent', 'OllamaAgent', 'make_agent', 'SYSTEM_PROMPT', 'httpx'):
        from . import legacy
        return getattr(legacy, name)
    raise AttributeError(name)
