"""Shared name-resolution budget, committed even when the following lookup fails."""
from contextvars import ContextVar
from fastapi import HTTPException
from .identity import quota, timestamp, transaction

peer_address = ContextVar('recipient_peer_address', default='local')


def limit(db, user):
    stamp = timestamp()
    with transaction(db) as conn:
        user_allowed = quota(conn, 'recipient:user', user.id, 30, 300, stamp)
        ip_allowed = quota(conn, 'recipient:ip', peer_address.get(), 60, 300, stamp)
    if not (user_allowed and ip_allowed):
        raise HTTPException(429, 'Too many recipient lookups. Try again later.',
                            headers={'Retry-After': str(300 - stamp % 300)})
