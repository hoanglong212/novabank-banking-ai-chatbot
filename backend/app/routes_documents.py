"""Four authenticated document endpoints; bounded multipart, never a tool bypass."""
from fastapi import APIRouter, Depends, HTTPException, Request
from python_multipart import MultipartParser
from python_multipart.multipart import parse_options_header
from .dependencies import current_user, get_db
from .documents import service
from .documents.extract import MAX_BYTES
from .documents.repository import Repository

router = APIRouter(prefix='/api/documents')
MULTIPART_OVERHEAD_BYTES = 64 * 1024


async def read_upload(request):
    media, options = parse_options_header(request.headers.get('content-type', ''))
    if media != b'multipart/form-data' or not options.get(b'boundary'):
        raise HTTPException(415, 'MULTIPART_REQUIRED')
    data = bytearray()
    async for part in request.stream():
        if len(data) + len(part) > MAX_BYTES + MULTIPART_OVERHEAD_BYTES:
            raise HTTPException(422, 'FILE_TOO_LARGE')
        data.extend(part)
    state = {'headers': {}, 'key': bytearray(), 'value': bytearray(), 'count': 0, 'files': [], 'body': bytearray()}
    def begin():
        state.update(headers={}, key=bytearray(), value=bytearray(), body=bytearray())
        state['count'] += 1
        if state['count'] > 10:
            raise ValueError('Too many fields')
    def field(d, s, e):
        state['key'].extend(d[s:e])
    def value(d, s, e):
        state['value'].extend(d[s:e])
    def header_end():
        state['headers'][bytes(state['key']).lower()] = bytes(state['value'])
        state.update(key=bytearray(), value=bytearray())
    def body(d, s, e):
        state['body'].extend(d[s:e])
    def end():
        _, opts = parse_options_header(state['headers'].get(b'content-disposition', b''))
        if opts.get(b'name') == b'file' and b'filename' in opts:
            state['files'].append((bytes(state['body']), opts[b'filename'].decode('utf-8', errors='replace')))
    complete = []
    try:
        parser = MultipartParser(options[b'boundary'], {
            'on_part_begin': begin, 'on_header_field': field, 'on_header_value': value,
            'on_header_end': header_end, 'on_part_data': body, 'on_part_end': end, 'on_end': lambda: complete.append(True)})
        parser.write(bytes(data))
        parser.finalize()
        if not complete or len(state['files']) != 1:
            raise ValueError('One file required')
    except Exception:
        raise HTTPException(422, 'INVALID_UPLOAD') from None
    return state['files'][0]


@router.post('', status_code=201)
async def upload(request: Request, user=Depends(current_user), db=Depends(get_db)):
    data, name = await read_upload(request)
    if len(data) > MAX_BYTES:
        raise HTTPException(422, 'FILE_TOO_LARGE')
    Repository(db, user.id).rate_limit()
    return await service.ingest(db, user.id, data, name)


@router.get('')
def listing(user=Depends(current_user), db=Depends(get_db)):
    return {'items': Repository(db, user.id).list()}


@router.get('/{document_id}')
def detail(document_id: str, user=Depends(current_user), db=Depends(get_db)):
    repo = Repository(db, user.id)
    doc = repo.get(document_id)
    if doc['status'] == 'ready':
        doc['preview'] = ''.join(row['text'] for row in repo.chunks(document_id)[:1])[:500]
    return doc


@router.delete('/{document_id}')
def delete(document_id: str, user=Depends(current_user), db=Depends(get_db)):
    Repository(db, user.id).delete(document_id)
    return {'deleted': True}
