"""Simple environment-driven application config."""
import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def setting(name: str, default: str = '') -> str:
    return os.environ.get(name, default)


def provider() -> str:
    value = setting('LLM_PROVIDER', 'mock').lower()
    if value not in ('mock', 'ollama'):
        raise ValueError('LLM_PROVIDER must be mock or ollama')
    return value
