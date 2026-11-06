"""Compatibility alias for app.agent.graph_agent."""
import sys
from .agent import graph_agent as _implementation
sys.modules[__name__] = _implementation
