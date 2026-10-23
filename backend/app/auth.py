"""Demo account metadata; authentication lives in sessions.py."""
from dataclasses import dataclass


@dataclass(frozen=True)
class DemoPrincipal:
    id: str
    name: str
    accounts: tuple[str, ...]


DEMO_USERS = (
    DemoPrincipal('alice', 'Alice', ('ACC-ALICE-001',)),
    DemoPrincipal('bob', 'Bob', ('ACC-BOB-001',)),
)
