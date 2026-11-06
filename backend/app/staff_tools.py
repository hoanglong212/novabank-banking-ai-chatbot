"""Read-only staff capabilities, selected from the authenticated database role."""
import re
from fastapi import HTTPException
from pydantic import Field
from .auth import ROLE_PERMISSIONS
from .identity_schemas import IdentityInput


class TicketArgs(IdentityInput):
    ticket_id: str = Field(min_length=3, max_length=80)


class TransactionsArgs(IdentityInput):
    limit: int = Field(default=10, ge=1, le=50)
    mask: bool = True


PERMISSIONS = {'list_tickets': 'support:read', 'read_ticket': 'support:read',
               'get_user_count': 'settings:write', 'list_transactions': 'admin:transactions:read'}


def allowed(role):
    permissions = ROLE_PERMISSIONS.get(role, frozenset())
    return {tool for tool, permission in PERMISSIONS.items() if permission in permissions}


def bind(content):
    text = content.lower()
    ticket = re.search(r'\bTKT-[A-Za-z0-9]+\b', content, re.I)
    if ticket:
        return {'text': content, 'tool': 'read_ticket', 'arguments': {'ticket_id': ticket.group().upper()}}
    name = 'get_user_count' if 'user' in text else 'list_transactions' if 'transaction' in text else 'list_tickets'
    return {'text': content, 'tool': name, 'arguments': {}}


def execute(conn, user, name, args, intent):
    if name not in allowed(user.role):
        raise HTTPException(403, 'ROLE_NOT_PERMITTED')
    if name == 'get_user_count':
        return {'count': conn.execute('SELECT COUNT(*) FROM users').fetchone()[0]}
    if name == 'list_tickets':
        return {'items': [dict(r) for r in conn.execute('SELECT id,subject,status FROM support_tickets ORDER BY created_at DESC LIMIT 20')], 'trust_level': 'untrusted'}
    if name == 'read_ticket':
        if args['ticket_id'].casefold() not in intent['text'].casefold():
            raise HTTPException(403, 'USER_INTENT_REQUIRED')
        row = conn.execute('SELECT id,subject,description,status FROM support_tickets WHERE id=?', (args['ticket_id'],)).fetchone()
        if not row:
            raise HTTPException(404, 'TICKET_NOT_FOUND')
        return {**dict(row), 'trust_level': 'untrusted'}
    # Masking is mandatory; a model cannot turn it off by passing mask=false.
    if not args['mask']:
        raise HTTPException(403, 'MASK_REQUIRED')
    return {'items': [dict(r) for r in conn.execute('SELECT id,amount_vnd,direction,status,date FROM transactions ORDER BY date DESC LIMIT ?', (args['limit'],))], 'masked': True}
