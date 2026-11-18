"""Simple environment-driven application config."""
import os
import sys
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).resolve().parents[1] / '.env')


def setting(name: str, default: str = '') -> str:
    return os.environ.get(name, default)


def legacy_test_mode() -> bool:
    """Legacy execution exists only inside an explicitly opted-in running test."""
    return (setting('LEGACY_AGENT_TEST_MODE') == 'true'
            and 'pytest' in sys.modules
            and bool(setting('PYTEST_CURRENT_TEST').strip()))


def provider() -> str:
    value = setting('LLM_PROVIDER', 'mock').lower()
    if value not in ('mock', 'ollama', 'langgraph'):
        raise ValueError('LLM_PROVIDER must be mock, ollama or langgraph')
    return value
