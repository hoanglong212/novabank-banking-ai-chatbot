"""Bank-owned document attribution; audit references never contain source prose."""
import json
import re
from fastapi import HTTPException
from .repository import Repository
from ..auth_crypto import decrypt_secret
from ..guard import BARE_TOKEN


def is_read(conn, db, run):
    return bool(conn.execute("SELECT 1 FROM agent_calls WHERE run_id=? AND name='ask_document'", (run['id'],)).fetchone()
        or json.loads(decrypt_secret(db, run['bound_request_json'])).get('tool') == 'ask_document')


def restore(conn, db, run, answer, vault):
    if not is_read(conn, db, run):
        return vault.restore(answer)
    allowed = set()
    for row in conn.execute("SELECT result_json FROM agent_calls WHERE run_id=? AND name='ask_document' AND decision='ALLOW'", (run['id'],)):
        allowed.update(json.loads(row[0]).get('aliases', []))
    intent = json.loads(decrypt_secret(db, run['bound_request_json']))
    for alias, real in vault.real.items():
        if re.search(r'(?<!\w)' + re.escape(real) + r'(?!\w)', intent.get('text',''), re.I):
            allowed.add(alias.strip('<>'))
    return BARE_TOKEN.sub(lambda m: vault.real.get('<'+m.group(1)+'>', '[unverified reference]')
        if m.group(1) in allowed else '[unverified reference]', answer)


def unfiltered_answer(conn, db, run, answer, vault):
    answer = restore(conn, db, run, answer, vault)
    return attribute(conn, db, run, answer) if is_read(conn, db, run) else answer

def cited_document(conn, db, run):
    rows = conn.execute("""SELECT result_json FROM agent_calls
        WHERE run_id=? AND name='ask_document' AND decision='ALLOW' ORDER BY ordinal DESC""", (run['id'],))
    for row in rows:
        evidence = json.loads(row[0])
        if not evidence.get('found'):
            continue
        try:
            doc = Repository(db, run['owner_id']).get(evidence.get('document_id'), ready=True)
        except HTTPException:
            continue
        chunks = [c for c in Repository(db, run['owner_id']).chunks(doc['id'])
                  if c['id'] in evidence.get('cited_chunk_ids', [])]
        if chunks:
            return doc, chunks
    return None


def attribute(conn, db, run, answer):
    evidence = cited_document(conn, db, run)
    if not evidence:
        return 'I could not verify an answer from this document. Select a ready document and try again.'
    # Filename is displayed as plain text, not a link or Markdown instruction.
    name = re.sub(r'[\[\]<>*_`#]|(?:https?://|www\.)\S+', '', evidence[0]['filename_display'], flags=re.I)
    return 'According to document "' + name + '":\n' + answer

