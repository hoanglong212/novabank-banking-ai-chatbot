"""Compatibility alias for app.agent.agent_access."""
import sys
from .agent import agent_access as _implementation
sys.modules[__name__] = _implementation
