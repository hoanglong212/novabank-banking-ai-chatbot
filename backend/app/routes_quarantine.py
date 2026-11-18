from fastapi import APIRouter, Depends, HTTPException
from pydantic import Field
from .database import now
from .dependencies import get_db, require_permission
from .identity import transaction
from .identity_schemas import IdentityInput
from .posting import audit

router = APIRouter(prefix='/api/agent/quarantine')
reviewer = require_permission('support:write')


class Release(IdentityInput):
    reason: str = Field(min_length=5, max_length=300)


@router.get('')
def list_sources(user=Depends(reviewer), db=Depends(get_db)):
    with db.connect() as conn:
        return {'items': [dict(row) for row in conn.execute('SELECT * FROM quarantined_sources WHERE released_at IS NULL ORDER BY created_at DESC LIMIT 100')]}


@router.post('/{source_id}/release')
def release(source_id: str, payload: Release, user=Depends(reviewer), db=Depends(get_db)):
    with transaction(db) as conn:
        row = conn.execute('SELECT * FROM quarantined_sources WHERE source_id=?', (source_id,)).fetchone()
        if not row:
            raise HTTPException(404, 'Source not found.')
        if row['released_at'] is None:
            conn.execute('UPDATE quarantined_sources SET released_at=? WHERE source_id=?', (now(), source_id))
            audit(conn, user.id, 'SOURCE_RELEASED', source_id, payload.reason, now())
    return {'message': 'Source released after staff review.'}
