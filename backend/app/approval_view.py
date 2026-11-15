"""Human review metadata from frozen bank records, never model narration."""
import json

TITLES = {'prepare_transfer_limit': 'Review your transfer limit', 'prepare_transfer': 'Review your transfer', 'prepare_bill_payment': 'Review your bill payment',
    'prepare_support_ticket': 'Review your support request', 'request_card_freeze': 'Review your card freeze',
    'propose_ticket_reply': 'Review your ticket reply', 'propose_ticket_status': 'Review the ticket status',
    'propose_account_status': 'Review the account status', 'propose_customer_update': 'Review customer access',
    'propose_settings_change': 'Review bank settings', 'propose_reconciliation': 'Review reconciliation'}
EXPLANATIONS = {'bank-approval': 'Check the exact details before approving. A payment still requires separate bank verification.',
    'large-transfer': 'This amount requires extra care. Verify the recipient independently.',
    'A-lab-control': 'This is a restricted research configuration. Bank approval and payment verification are still required.',
    'B-bank-approval': 'Review the payment details; the bank will request a separate verification code.'}


def review(conn, approval):
    row = conn.execute('SELECT * FROM approval_risk WHERE approval_id=?', (approval['id'],)).fetchone()
    risk = dict(row) if row else {}
    features = json.loads(risk.get('features_json', '{}'))
    origins = json.loads(risk.get('origins_json', '{}'))
    rules = json.loads(risk.get('rule_ids_json', '[]'))
    labels = {'user': 'From your confirmed message', 'bank_default': 'Selected by the bank as your primary payment account'}
    level = risk.get('band', 'not_evaluated')
    return {'title': TITLES.get(approval['name'], 'Review this proposed action'), 'frozen': True,
        'risk_band': level, 'risk_label': {'low': 'Low', 'medium': 'Medium', 'high': 'High', 'very_high': 'Very high', 'not_evaluated': 'Not assessed'}.get(level, 'Not assessed'),
        'new_recipient': bool(features.get('recipient_new')),
        'warning': 'New recipient. Verify their details independently before entering any bank code.' if features.get('recipient_new') else '',
        'not_before': risk.get('not_before', 0), 'parameter_sources': origins,
        'source_labels': {field: labels.get(origin, 'Proposed detail: verify it before approval') for field, origin in origins.items()},
        'rule_ids': rules, 'rule_explanations': [EXPLANATIONS.get(rule, 'The bank requires review of these exact details.') for rule in rules]}
