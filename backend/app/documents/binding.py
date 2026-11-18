"""Recognize document reads from the current user message, without a model."""
import re
from ..faq import fold

ID = re.compile(r'\b[0-9a-f]{8}-[0-9a-f]{4}-4[0-9a-f]{3}-[89ab][0-9a-f]{3}-[0-9a-f]{12}\b', re.I)


def requested(text):
    return bool(re.search(r'\b(?:document|documents|uploaded|invoice|contract|tai lieu|hop dong|hoa don|sao ke)\b', fold(text)))


def arguments(text):
    ids = ID.findall(text)
    return {'question': text[:1000], **({'document_id': ids[0].lower()} if len(set(ids)) == 1 else {})}


def resolve(db, owner, intent):
    if intent['tool'] != 'ask_document' or intent['arguments'].get('document_id'):
        return
    from fastapi import HTTPException
    from .repository import Repository
    rows = [r for r in Repository(db, owner).list() if r['status'] == 'ready']
    text = fold(intent['text']).replace('_', ' ')
    named = [r for r in rows if fold(r['filename_display'].rsplit('.', 1)[0]).replace('_', ' ') in text]
    choices = named if named else rows
    if len(choices) != 1:
        raise HTTPException(400, 'Choose one ready document in My documents, then ask your question.')
    intent['arguments']['document_id'] = choices[0]['id']
