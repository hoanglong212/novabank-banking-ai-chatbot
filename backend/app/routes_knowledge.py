from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query
from pydantic import Field
from . import knowledge
from .database import now
from .dependencies import current_user, get_db, require_permission
from .identity import transaction
from .identity_schemas import IdentityInput
from .posting import audit

router = APIRouter(prefix='/api')


class Document(IdentityInput):
    title: str = Field(min_length=3, max_length=160)
    content: str = Field(min_length=10, max_length=20000)
    source: str = Field(min_length=1, max_length=250)
    trust_level: Literal['approved', 'untrusted'] = 'untrusted'
    status: Literal['DRAFT', 'PUBLISHED'] = 'DRAFT'


@router.get('/knowledge')
def documents(user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        where = '' if 'settings:write' in user.permissions else " WHERE status='PUBLISHED' AND trust_level='approved'"
        return {'items': [dict(r) for r in conn.execute('SELECT id,title,content,source,trust_level,status,updated_at FROM knowledge_documents' + where + ' ORDER BY title LIMIT 200')]}


@router.get('/knowledge/search')
async def search(q: str = Query(min_length=1, max_length=500), user=Depends(current_user), db=Depends(get_db)):
    return await knowledge.search(db, q)


@router.get('/knowledge/{document_id}')
def document(document_id: str, user=Depends(current_user), db=Depends(get_db)):
    with db.connect() as conn:
        row = conn.execute('SELECT id,title,content,source,trust_level,status,updated_at FROM knowledge_documents WHERE id=?', (document_id,)).fetchone()
        if not row or ('settings:write' not in user.permissions and (row['status'] != 'PUBLISHED' or row['trust_level'] != 'approved')):
            raise HTTPException(404, 'Document not found.')
        return dict(row)


@router.post('/admin/knowledge', status_code=201)
def create(payload: Document, user=Depends(require_permission('settings:write')), db=Depends(get_db)):
    key = 'KB-' + uuid.uuid4().hex[:12]
    with transaction(db) as conn:
        conn.execute('''INSERT INTO knowledge_documents (id,title,content,source,trust_level,status,created_at,updated_at)
            VALUES (?,?,?,?,?,?,?,?)''', (key, payload.title, payload.content, payload.source, payload.trust_level, payload.status, now(), now()))
        audit(conn, user.id, 'KNOWLEDGE_CREATED', key, payload.status, now())
    return {'id': key, 'message': 'Document created. Rebuild the search index after publishing.'}


@router.put('/admin/knowledge/{document_id}')
def update(document_id: str, payload: Document, user=Depends(require_permission('settings:write')), db=Depends(get_db)):
    with transaction(db) as conn:
        if not conn.execute('UPDATE knowledge_documents SET title=?,content=?,source=?,trust_level=?,status=?,updated_at=? WHERE id=?',
                            (payload.title, payload.content, payload.source, payload.trust_level, payload.status, now(), document_id)).rowcount:
            raise HTTPException(404, 'Document not found.')
        conn.execute('DELETE FROM knowledge_chunks WHERE document_id=?', (document_id,))
        audit(conn, user.id, 'KNOWLEDGE_UPDATED', document_id, payload.status, now())
    return {'message': 'Document updated. Its old index was invalidated.'}


@router.post('/admin/knowledge-index')
async def reindex(user=Depends(require_permission('settings:write')), db=Depends(get_db)):
    return await knowledge.index(db)
