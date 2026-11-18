"""Bank-owned document attribution; audit references never contain source prose."""
import json
import re
from fastapi import HTTPException
from .repository import Repository

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

