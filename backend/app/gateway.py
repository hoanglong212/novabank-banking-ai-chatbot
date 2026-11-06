"""Compatibility alias for app.agent.gateway."""
import sys
from .agent import gateway as _implementation
sys.modules[__name__] = _implementation
