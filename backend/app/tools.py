"""Compatibility alias for app.agent.tools."""
import sys
from .agent import tools as _implementation
sys.modules[__name__] = _implementation
