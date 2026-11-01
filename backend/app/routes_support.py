"""Customer tickets and staff replies; customer text remains untrusted data."""
import base64
import binascii
from pathlib import PurePath
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from .action_security import notify
from .database import now
from .dependencies import current_user, get_db, require_permission
from .identity import transaction
from .identity_schemas import IdentityInput

router = APIRouter(prefix='/api/support')


def ticket(conn, user, ticket_id):
    row = conn.execute('SELECT * FROM support_tickets WHERE id=?', (ticket_id,)).fetchone()
    if not row or (row['owner_id'] != user.id and 'support:read' not in user.permissions):
        raise HTTPException(404, 'Ticket not found.')
    return dict(row)


class TicketInput(IdentityInput):
    subject: str = Field(min_length=3, max_length=160)
    description: str = Field(min_length=5, max_length=5000)
    category: Literal['GENERAL', 'PAYMENT', 'CARD', 'ACCOUNT', 'SECURITY'] = 'GENERAL'


class Reply(IdentityInput):
    body: str = Field(min_length=1, max_length=5000)


class Assignment(IdentityInput):
    status: Literal['OPEN', 'IN_PROGRESS', 'RESOLVED', 'CLOSED']
    assigned_to: str | None = Field(default=None, max_length=64)


class Attachment(IdentityInput):
    name: str = Field(min_length=1, max_length=120)
    content_base64: str = Field(max_length=2800000)


@router.get('/tickets')
def tickets(user=Depends(current_user), db=Depends(get_db), offset: int = Query(0, ge=0), limit: int = Query(20, ge=1, le=100)):
    if user.role == 'operations':
        raise HTTPException(403, 'Permission denied')
    where, params = ('', []) if 'support:read' in user.permissions else (' WHERE t.owner_id=?', [user.id])
    with db.connect() as conn:
        total = conn.execute('SELECT COUNT(*) FROM support_tickets t' + where, params).fetchone()[0]
        rows = conn.execute('''SELECT t.*,a.assigned_to,COALESCE(a.category,'GENERAL') AS category
            FROM support_tickets t LEFT JOIN ticket_assignments a ON a.ticket_id=t.id''' + where +
            ' ORDER BY t.created_at DESC,t.id DESC LIMIT ? OFFSET ?', (*params, limit, offset))
        return {'items': [dict(r) for r in rows], 'total': total, 'limit': limit, 'offset': offset}


@router.post('/tickets', status_code=201)
def create(payload: TicketInput, user=Depends(current_user), db=Depends(get_db)):
    from .action_security import limit
    limit(db, user)
    with transaction(db) as conn:
        ticket_id = 'TKT-' + uuid.uuid4().hex[:12].upper()
        conn.execute('INSERT INTO support_tickets VALUES (?,?,?,?,?,?)', (ticket_id, user.id, payload.subject, payload.description, 'OPEN', now()))
        conn.execute('INSERT INTO ticket_assignments VALUES (?,NULL,?)', (ticket_id, payload.category))
        return ticket(conn, user, ticket_id)


@router.get('/tickets/{ticket_id}')
def detail(ticket_id: str, user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        result = ticket(conn, user, ticket_id)
        result['trust_level'] = 'untrusted'
        result['messages'] = [dict(r) for r in conn.execute('SELECT * FROM ticket_messages WHERE ticket_id=? ORDER BY created_at,rowid', (ticket_id,))]
        result['attachments'] = [dict(r) for r in conn.execute('SELECT id,name,media_type,length(content) AS size_bytes,created_at FROM ticket_attachments WHERE ticket_id=? ORDER BY created_at,rowid', (ticket_id,))]
        row = conn.execute('SELECT * FROM ticket_assignments WHERE ticket_id=?', (ticket_id,)).fetchone()
        result['assigned_to'] = row['assigned_to'] if row else None
        return result


@router.post('/tickets/{ticket_id}/messages', status_code=201)
def reply(ticket_id: str, payload: Reply, user=Depends(current_user), db=Depends(get_db)):
    with transaction(db) as conn:
        row = ticket(conn, user, ticket_id)
        if row['status'] == 'CLOSED':
            raise HTTPException(409, 'This ticket is closed. Create a new ticket for further help.')
        if row['owner_id'] != user.id and 'support:write' not in user.permissions:
            raise HTTPException(403, 'Permission denied.')
        message_id = uuid.uuid4().hex
        conn.execute('INSERT INTO ticket_messages VALUES (?,?,?,?,?)', (message_id, ticket_id, user.id, payload.body, now()))
        if row['owner_id'] != user.id:
            notify(conn, row['owner_id'], 'SUPPORT', 'Support replied', row['subject'], now(), ticket_id)
        return {'id': message_id, 'message': 'Reply sent.'}


@router.patch('/tickets/{ticket_id}')
def assign(ticket_id: str, payload: Assignment, user=Depends(require_permission('support:write')), db=Depends(get_db)):
    with transaction(db) as conn:
        row = ticket(conn, user, ticket_id)
        if payload.assigned_to:
            assignee = conn.execute("SELECT 1 FROM users WHERE id=? AND role IN ('support','admin') AND status='ACTIVE'", (payload.assigned_to,)).fetchone()
            if not assignee:
                raise HTTPException(422, 'Choose an active support or admin user.')
        conn.execute('UPDATE support_tickets SET status=? WHERE id=?', (payload.status, ticket_id))
        conn.execute('INSERT INTO ticket_assignments (ticket_id,assigned_to) VALUES (?,?) ON CONFLICT(ticket_id) DO UPDATE SET assigned_to=excluded.assigned_to', (ticket_id, payload.assigned_to))
        notify(conn, row['owner_id'], 'SUPPORT', 'Ticket updated', f'{ticket_id}: {payload.status.replace("_", " ")}', now(), ticket_id)
    return {'message': 'Ticket updated.'}


def attachment_bytes(payload):
    try:
        content = base64.b64decode(payload.content_base64, validate=True)
    except (ValueError, binascii.Error):
        raise HTTPException(422, 'Invalid attachment encoding.')
    if not 1 <= len(content) <= 2 * 1024 * 1024:
        raise HTTPException(422, 'Attachments must be between 1 byte and 2 MB.')
    suffix = PurePath(payload.name).suffix.lower()
    signatures = {'.png': (b'\x89PNG\r\n\x1a\n', 'image/png'), '.jpg': (b'\xff\xd8\xff', 'image/jpeg'),
                  '.jpeg': (b'\xff\xd8\xff', 'image/jpeg'), '.pdf': (b'%PDF-', 'application/pdf')}
    if suffix == '.txt':
        try:
            content.decode('utf-8')
        except UnicodeDecodeError:
            raise HTTPException(422, 'Text attachments must use UTF-8.')
        media = 'text/plain'
    elif suffix in signatures and content.startswith(signatures[suffix][0]):
        media = signatures[suffix][1]
    else:
        raise HTTPException(422, 'Use a PNG, JPEG, PDF or UTF-8 text attachment with matching content.')
    return content, media


@router.post('/tickets/{ticket_id}/attachments', status_code=201)
def upload(ticket_id: str, payload: Attachment, user=Depends(current_user), db=Depends(get_db)):
    content, media = attachment_bytes(payload)
    with transaction(db) as conn:
        row = ticket(conn, user, ticket_id)
        if row['status'] == 'CLOSED':
            raise HTTPException(409, 'Ticket is closed.')
        if row['owner_id'] != user.id and 'support:write' not in user.permissions:
            raise HTTPException(403, 'Permission denied.')
        if conn.execute('SELECT COUNT(*) FROM ticket_attachments WHERE ticket_id=?', (ticket_id,)).fetchone()[0] >= 5:
            raise HTTPException(409, 'Each ticket supports up to five attachments.')
        attachment_id = uuid.uuid4().hex
        safe_name = payload.name.replace('\\', '/').split('/')[-1]
        conn.execute('INSERT INTO ticket_attachments VALUES (?,?,?,?,?,?,?)', (attachment_id, ticket_id, user.id, safe_name, media, content, now()))
    return {'id': attachment_id, 'name': safe_name, 'size_bytes': len(content)}


@router.get('/attachments/{attachment_id}')
def download(attachment_id: str, user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute('SELECT * FROM ticket_attachments WHERE id=?', (attachment_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Attachment not found.')
        ticket(conn, user, row['ticket_id'])
    suffix = PurePath(row['name']).suffix.lower()
    return Response(row['content'], media_type='application/octet-stream', headers={
        'Content-Disposition': f'attachment; filename="NovaBank-attachment-{attachment_id}{suffix}"',
        'X-Content-Type-Options': 'nosniff', 'Cache-Control': 'no-store', 'Content-Security-Policy': 'sandbox'})
