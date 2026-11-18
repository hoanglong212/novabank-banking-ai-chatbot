"""Bank-owned ingest and owner-scoped vector retrieval; outages fail closed."""
import hashlib
import json
import math
import re
import numpy as np
import httpx
from fastapi import HTTPException
from ..identity import transaction
from ..security_events import emit
from ..agent.source_screen import classify as screen
from ..config import setting, provider
from .binding import MAX_SUMMARY_PASSAGES, summary_requested
from .repository import Repository
from .extract import extract, filename, Rejected
from .privacy import prepare, register


def event(db, owner, kind, key, digest, rule):
    with transaction(db) as conn:
        emit(conn, kind, user_id=owner, source_ids=[key], rule_id=rule,
             detail={'document_id': key, 'sha256': digest})


def valid_vectors(vectors, count):
    return (isinstance(vectors, list) and len(vectors) == count and count > 0
        and all(isinstance(v, list) and 0 < len(v) <= 8192 for v in vectors)
        and len({len(v) for v in vectors}) == 1
        and all(type(x) in (int, float) and math.isfinite(x) for v in vectors for x in v)
        and all(any(x != 0 for x in v) for v in vectors))


async def embed(texts):
    if provider() == 'mock':
        # Explicit offline demo mode only. Never fall back here after a real model error.
        vectors = []
        for text in texts:
            vector = [0.0] * 64
            for token in re.findall(r'\w+', text.casefold()) or ['empty']:
                vector[int.from_bytes(hashlib.sha256(token.encode()).digest()[:4], 'big') % 64] += 1
            vectors.append(vector)
        return 'mock-only-document-embedding', vectors
    model = setting('EMBEDDING_MODEL', 'nomic-embed-text:latest')
    async with httpx.AsyncClient(timeout=60, trust_env=False) as client:
        response = await client.post(setting('OLLAMA_URL', 'http://127.0.0.1:11434').rstrip('/') + '/api/embed',
            json={'model': model, 'input': texts, 'truncate': False, 'keep_alive': '5m'})
        response.raise_for_status()
        if len(response.content) > 200 * 8192 * 24:
            raise ValueError('Embedding response too large')
        vectors = response.json()['embeddings']
        if not valid_vectors(vectors, len(texts)):
            raise ValueError('Invalid embeddings')
        return model, vectors


async def ingest(db, owner, data, original_name):
    repo = Repository(db, owner)
    digest = hashlib.sha256(data).hexdigest()
    display = filename(original_name)
    mime = 'application/pdf' if data.startswith(b'%PDF-') else 'text/plain'
    key = repo.reserve(display, mime, len(data), digest)
    try:
        mime, chunks = extract(data)
    except Rejected as exc:
        repo.finish(key, 'rejected', str(exc))
        event(db, owner, 'doc_ingest', key, digest, str(exc))
        return repo.get(key)
    # Screen the filename as well: filenames are another untrusted text surface.
    try:
        vault = register([display, *chunks])
        for text in [display, *chunks]:
            verdict = await screen(prepare(text, vault))
            if verdict.get('method') == 'unavailable' or verdict.get('available') is False:
                repo.finish(key, 'scan_failed', 'SOURCE_GUARD_UNAVAILABLE')
                event(db, owner, 'doc_scan_failed', key, digest, 'SOURCE_GUARD_UNAVAILABLE')
                return repo.get(key)
            if verdict.get('injection') is not False:
                repo.finish(key, 'quarantined', 'SOURCE_INJECTION')
                event(db, owner, 'doc_quarantine', key, digest, 'SOURCE_INJECTION')
                return repo.get(key)
        model, vectors = await embed([prepare(text, vault) for text in chunks])
        if not valid_vectors(vectors, len(chunks)):
            raise ValueError('Invalid embeddings')
    except Exception:
        repo.finish(key, 'scan_failed', 'DOCUMENT_PROCESSING_UNAVAILABLE')
        event(db, owner, 'doc_scan_failed', key, digest, 'DOCUMENT_PROCESSING_UNAVAILABLE')
        return repo.get(key)
    repo.finish(key, 'ready', 'doc-source-clean', chunks, vectors, model)
    event(db, owner, 'doc_ingest', key, digest, 'doc-source-clean')
    return repo.get(key)


async def retrieve(db, owner, key, question, vault=None):
    repo = Repository(db, owner)
    doc = repo.get(key, ready=True)
    rows = repo.chunks(key)
    if not rows:
        raise HTTPException(404, 'DOCUMENT_UNAVAILABLE')
    vault = register([doc['filename_display'], *[row['text'] for row in rows]], vault)
    if summary_requested(question):
        if len(rows) > MAX_SUMMARY_PASSAGES:
            # Include the first and last passages and preserve document order.
            rows = [rows[i * (len(rows) - 1) // (MAX_SUMMARY_PASSAGES - 1)]
                    for i in range(MAX_SUMMARY_PASSAGES)]
        repo.get(key, ready=True)
        return doc, [{'id': row['id'], 'text': row['text']} for row in rows]
    try:
        model, vectors = await embed([prepare(question, vault)])
        if not valid_vectors(vectors, 1):
            raise ValueError('Invalid query embedding')
        others = [json.loads(row['embedding']) for row in rows]
        if not valid_vectors(others, len(rows)) or len(others[0]) != len(vectors[0]):
            raise ValueError('Embedding mismatch')
        if any(json.loads(row['screen_result'])['model'] != model for row in rows):
            raise ValueError('Model changed')
        matrix, query = np.asarray(others, dtype=np.float64), np.asarray(vectors[0], dtype=np.float64)
        scores = matrix @ query / (np.linalg.norm(matrix, axis=1) * np.linalg.norm(query))
        if not np.all(np.isfinite(scores)):
            raise ValueError('Invalid similarity')
        chosen = sorted(range(len(rows)), key=lambda i: (-float(scores[i]), rows[i]['seq']))[:4]
    except Exception:
        raise HTTPException(503, 'DOCUMENT_RETRIEVAL_UNAVAILABLE') from None
    repo.get(key, ready=True)  # Deletion while awaiting embedding must not release text.
    return doc, [{'id': rows[i]['id'], 'text': rows[i]['text']} for i in chosen]
