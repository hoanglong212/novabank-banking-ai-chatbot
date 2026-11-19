"""Bank-owned document attribution; audit references never contain source prose."""
import json
import re
from fastapi import HTTPException
from .binding import MAX_SUMMARY_PASSAGES, summary_requested
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
    row = conn.execute("""SELECT decision,result_json FROM agent_calls
        WHERE run_id=? AND name='ask_document' ORDER BY ordinal DESC LIMIT 1""", (run['id'],)).fetchone()
    if not row or row['decision'] != 'ALLOW':
        return None
    evidence = json.loads(row['result_json'])
    if not evidence.get('found') or not evidence.get('cited_chunk_ids'):
        return None
    repo = Repository(db, run['owner_id'])
    try:
        doc = repo.get(evidence.get('document_id'), ready=True)
        chunks = repo.chunks(doc['id'])
    except HTTPException:
        return None
    if set(evidence['cited_chunk_ids']) <= {chunk['id'] for chunk in chunks}:
        return doc, len(chunks)
    return None


def attribute(conn, db, run, answer):
    evidence = cited_document(conn, db, run)
    if not evidence:
        failure = conn.execute("SELECT reason,decision,result_json FROM agent_calls WHERE run_id=? AND name='ask_document' "
                               "ORDER BY ordinal DESC LIMIT 1", (run['id'],)).fetchone()
        if failure and failure[0] in ('DOCUMENT_READER_UNAVAILABLE', 'DOCUMENT_RETRIEVAL_UNAVAILABLE'):
            return 'The document is indexed, but the reader could not finish this question. Try again or ask about one section at a time.'
        if failure and failure[1] == 'ALLOW' and json.loads(failure[2]).get('found') is False:
            return 'I read the selected document, but could not verify an answer from its text. Try asking about a specific section.'
        return 'I could not verify an answer from this document. Select a ready document and try again.'
    # Filename is displayed as plain text, not a link or Markdown instruction.
    name = re.sub(r'[\[\]<>*`#]|(?:https?://|www\.)\S+', '', evidence[0]['filename_display'], flags=re.I)
    caveat = ''
    if evidence[1] > MAX_SUMMARY_PASSAGES:
        intent = json.loads(decrypt_secret(db, run['bound_request_json']))
        if summary_requested((intent.get('arguments') or {}).get('question', '')):
            caveat = '\n\nThis overview is based on selected passages from across the document.'
    return 'According to document "' + name + '":\n' + answer + caveat

