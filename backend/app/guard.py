"""Compatibility alias for app.agent.guard."""
import sys
from .agent import guard as _implementation
sys.modules[__name__] = _implementation
