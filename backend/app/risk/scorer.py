import json
import time
from ..agent import policy
from . import cases

DEFAULTS = {'floor_financial': 20, 'floor_account_change': 20, 'untrusted': 40,
            'new_recipient': 20, 'flagged_case': 20, 'medium': 20, 'high': 60, 'very_high': 80}


def band(value, settings=None):
    limits = {**DEFAULTS, **(settings or {})}
    return next((name for name in ('very_high', 'high', 'medium') if value >= limits[name]), 'low')


def score(features, neighbors=(), policy_band=None, settings=None):
    weights = {**DEFAULTS, **(settings or {})}
    if any(type(v) is not int or v < 0 or v > 100 for v in weights.values()):
        raise ValueError('Risk points must be nonnegative integers bounded by 100')
    if not 0 <= weights['medium'] < weights['high'] < weights['very_high'] <= 100:
        raise ValueError('Risk thresholds must increase')
    value = weights.get('floor_' + features.get('tier', 'read'), 0)
    value += weights['untrusted'] if features.get('context_label') == 'UNTRUSTED' else 0
    value += weights['new_recipient'] if features.get('recipient_new') else 0
    value += weights['flagged_case'] * sum(item.get('decision') == 'deny_and_flag' for item in neighbors)
    value = min(100, max(value, weights.get(policy_band, 0)))
    return {'score': value, 'band': band(value, weights)}


def prepare(conn, user, run, name, args, approval_id, origins, ruling):
    row = conn.execute('SELECT context_label,risk_score FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
    recipient = args.get('to_account')
    new = is_new_recipient(conn, user.id, args) if recipient else False
    features = {'tool': name, 'tier': 'financial' if name in ('prepare_transfer', 'prepare_bill_payment') else 'account_change',
        'context_label': row[0], 'recipient_new': new,
        'amount_bucket': 'large' if args.get('amount_vnd', 0) >= 1000000 else 'small', 'config': run['config']}
    risk = policy.load(run['config'])['risk']
    weights = risk.get('points', DEFAULTS)
    active = policy.layer_enabled(run, 'risk_signals')
    scored = score(features, cases.nearest(conn, features), ruling['action'].removeprefix('band_') if ruling['action'].startswith('band_') else None, weights) if active else {'score': 0, 'band': 'not_evaluated'}
    if active:
        scored['score'] = max(row[1], scored['score'])
        scored['band'] = band(scored['score'], weights)
    wait = risk.get('new_recipient_wait_seconds')
    if type(wait) is not int or not 0 <= wait <= 86400:
        raise ValueError('Invalid configured waiting interval')
    not_before = int(time.time()) + wait if active and new and scored['band'] in ('high', 'very_high') else 0
    conn.execute('INSERT INTO approval_risk VALUES (?,?,?,?,?,?,?,?)', (approval_id, run['id'], scored['score'], scored['band'], not_before,
        json.dumps(features), json.dumps(origins), json.dumps([ruling['rule_id']])))
    conn.execute('UPDATE agent_runs SET risk_features_json=?,risk_score=MAX(risk_score,?),risk_decision=? WHERE id=?',
        (json.dumps(features), scored['score'], ruling['action'], run['id']))
    return {**scored, 'new_recipient': new, 'not_before': not_before}


def guard_otp(conn, transfer_id):
    from ..posting import TransferError
    row = conn.execute("SELECT r.not_before FROM approval_risk r JOIN tool_approvals a ON a.id=r.approval_id WHERE json_extract(a.response_json,'$.draft_id')=?", (transfer_id,)).fetchone()
    if row and row[0] > int(time.time()):
        raise TransferError('RECIPIENT_COOLING_OFF')


def observe(conn, user, run, name, args, decision, reason, *, policy_action=None):
    """Termination evidence includes rejected actions, not just approved drafts."""
    row = conn.execute('SELECT context_label,risk_score,risk_decision FROM agent_runs WHERE id=?', (run['id'],)).fetchone()
    recipient = args.get('to_account')
    new = is_new_recipient(conn, user.id, args) if recipient else False
    tier = 'financial' if name in ('prepare_transfer', 'prepare_bill_payment') else 'account_change' if name.startswith(('prepare_', 'propose_', 'request_')) else 'read'
    features = {'tool': name, 'tier': tier, 'context_label': row[0], 'recipient_new': new,
                'amount_bucket': 'large' if args.get('amount_vnd', 0) >= 1000000 else 'small', 'config': run['config']}
    flagged = decision == 'DENY' and (policy_action == 'deny_and_flag' or (policy_action is None and reason in ('SOURCE_INJECTION', 'PARAM_FROM_UNTRUSTED', 'T4-bind')))
    verdict = 'deny_and_flag' if flagged or row[2] == 'deny_and_flag' else 'deny' if decision != 'ALLOW' else row[2]
    value = score(features, cases.nearest(conn, features), settings=policy.load(run['config'])['risk'].get('points'))['score'] if policy.layer_enabled(run, 'risk_signals') else 0
    # Preserve the most consequential action's features for case matching.
    if flagged or value >= row[1]:
        conn.execute('UPDATE agent_runs SET risk_features_json=?,risk_score=MAX(risk_score,?),risk_decision=? WHERE id=?',
                     (json.dumps(features), value, verdict, run['id']))


def is_new_recipient(conn, owner_id, args):
    from ..transfer_stepup import new_recipient
    from ..faq import fold
    bank = args.get('to_bank', 'NovaBank')
    if fold(bank).replace(' ', '') in ('novabank', 'nova', 'nvb'):
        bank = 'NovaBank'
    return new_recipient(conn, {'owner_id': owner_id, 'to_bank': bank, 'to_account': args['to_account']})
