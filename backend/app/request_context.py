"""Correlation metadata only; request IDs never grant authority."""
from contextvars import ContextVar

request_id = ContextVar('request_id', default='')


def initialize(conn):
    for table in ('agent_runs', 'agent_calls', 'tool_events'):
        columns = {r[1] for r in conn.execute(f'PRAGMA table_info({table})')}
        if 'request_id' not in columns:
            conn.execute(f"ALTER TABLE {table} ADD COLUMN request_id TEXT NOT NULL DEFAULT ''")
