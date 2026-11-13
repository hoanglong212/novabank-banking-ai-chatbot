"""Compatibility alias for app.agent.agent_guard."""
import sys
from .agent import agent_guard as _implementation
sys.modules[__name__] = _implementation
