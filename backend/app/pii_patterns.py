"""Contextual Presidio prototype; not yet wired into the model request pipeline."""
import re
from presidio_analyzer import Pattern, PatternRecognizer
from .faq import fold

PHONE = PatternRecognizer(supported_entity='VN_PHONE',supported_language='en',patterns=[
    Pattern(name='vn_phone',regex=r'(?<!\d)(?:\+84[ .-]?|0)[35789](?:[ .-]?\d){8}(?!\d)',score=.8)])


def phone_entities(text: str):
    results = []
    for hit in PHONE.analyze(text=text,entities=['VN_PHONE']):
        before = fold(text[max(0,hit.start-50):hit.start])
        after = fold(text[hit.end:hit.end+16])
        money_suffix = re.match(r'^\s*(?:vnd\b|dong\b|d\b|₫)',after)
        money_prefix = re.search(r'\b(?:so tien|amount|chuyen)\s*:?\s*$',before)
        if not money_suffix and not money_prefix:
            results.append(hit)
    return results
