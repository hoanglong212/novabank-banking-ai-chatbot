"""Strict JSON policy interpreter: no eval, plugins, or model decisions."""
import json
import math
from pathlib import Path
from fastapi import HTTPException

POLICY_DIR = Path(__file__).with_name('policies')
LAYERS = frozenset(('spotlighting', 'classifier', 'provenance', 'intent_binding', 'approval_otp', 'output_filter', 'risk_signals', 'quarantine', 'dual_llm'))
ACTIONS = frozenset(('deny_and_flag', 'deny', 'band_very_high', 'band_high', 'approve_with_otp', 'allow'))
CONDITIONS = frozenset(('arg_not_from_user', 'context', 'recipient_new', 'args', 'tool', 'role'))
OPS = {'gt': lambda a, b: a > b, 'gte': lambda a, b: a >= b, 'lt': lambda a, b: a < b, 'lte': lambda a, b: a <= b, 'eq': lambda a, b: a == b}


class PolicyDenied(HTTPException):
    """Carry the bank-evaluated action independently of a configurable rule name."""
    def __init__(self, ruling):
        super().__init__(403, ruling['rule_id'])
        self.ruling = dict(ruling)


def _object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError('Duplicate policy key')
        value[key] = item
    return value


def load(config):
    if config not in ('A', 'B', 'C', 'D'):
        raise ValueError('Unknown policy configuration')
    data = json.loads((POLICY_DIR / (config + '.json')).read_text(encoding='utf-8'), object_pairs_hook=_object,
                      parse_constant=lambda _: (_ for _ in ()).throw(ValueError('Nonfinite policy constant')))
    if not isinstance(data, dict) or set(data) != {'config', 'layers', 'rules', 'risk'} or data['config'] != config:
        raise ValueError('Invalid policy document')
    layers = data['layers']
    if not isinstance(layers, dict) or set(layers) != LAYERS or any(type(v) is not bool for v in layers.values()) or not layers['approval_otp']:
        raise ValueError('Bank approval and verification cannot be disabled')
    if not isinstance(data['risk'], dict) or not isinstance(data['rules'], list) or not data['rules']:
        raise ValueError('Policy rules/risk are required')
    risk = data['risk']
    if set(risk) - {'new_recipient_wait_seconds', 'points'} or type(risk.get('new_recipient_wait_seconds')) is not int or not 0 <= risk['new_recipient_wait_seconds'] <= 86400:
        raise ValueError('Invalid risk configuration')
    from ..risk.scorer import DEFAULTS, score
    points = risk.get('points', DEFAULTS)
    if not isinstance(points, dict) or set(points) != set(DEFAULTS):
        raise ValueError('Explicit risk points must name every configured weight')
    score({}, settings=points)
    ids = set()
    for rule in data['rules']:
        if not isinstance(rule, dict) or set(rule) != {'id', 'priority', 'when', 'then'}:
            raise ValueError('Invalid policy rule')
        if not isinstance(rule['id'], str) or not rule['id'] or rule['id'] in ids or type(rule['priority']) is not int or rule['then'] not in ACTIONS:
            raise ValueError('Invalid policy identity/action')
        ids.add(rule['id'])
        when = rule['when']
        if not isinstance(when, dict) or set(when) - CONDITIONS:
            raise ValueError('Unsupported policy condition')
        for key, value in when.items():
            if key in ('arg_not_from_user', 'recipient_new') and type(value) is not bool:
                raise ValueError('Boolean policy condition required')
            if key == 'context' and value not in ('TRUSTED', 'UNTRUSTED'):
                raise ValueError('Invalid context condition')
            if key in ('tool', 'role') and not (isinstance(value, str) or isinstance(value, list) and all(isinstance(v, str) for v in value)):
                raise ValueError('Invalid tool/role condition')
            if key == 'args':
                if not isinstance(value, dict):
                    raise ValueError('Invalid numeric conditions')
                for comparisons in value.values():
                    if not isinstance(comparisons, dict) or not comparisons or set(comparisons) - OPS.keys():
                        raise ValueError('Unsupported comparison')
                    if any(type(v) not in (int, float) or not math.isfinite(v) for v in comparisons.values()):
                        raise ValueError('Finite numeric operands required')
    return data


def _matches(when, facts):
    for key, expected in when.items():
        actual = facts.get(key)
        if key == 'args':
            for field, comparisons in expected.items():
                number = (actual or {}).get(field)
                if type(number) not in (int, float) or not math.isfinite(number) or not all(OPS[op](number, value) for op, value in comparisons.items()):
                    return False
        elif isinstance(expected, list):
            if actual not in expected:
                return False
        elif type(actual) is not type(expected) or actual != expected:
            return False
    return True


def evaluate(config, facts):
    try:
        data = load(config)
        for rule in sorted(data['rules'], key=lambda r: r['priority']):
            if _matches(rule['when'], facts):
                return {'action': rule['then'], 'rule_id': rule['id']}
        return {'action': 'deny', 'rule_id': 'NO_MATCHING_POLICY'}
    except (OSError, ValueError, KeyError, TypeError, OverflowError):
        return {'action': 'deny', 'rule_id': 'POLICY_UNAVAILABLE'}


def layer_enabled(run, name):
    try:
        return load(run.get('config') or ('A' if run.get('gateway') == 'off' else 'D'))['layers'][name]
    except (OSError, ValueError, KeyError, TypeError):
        raise HTTPException(503, 'POLICY_UNAVAILABLE')


def initialize(conn, stamp):
    if conn.execute('SELECT 1 FROM schema_migrations WHERE version=14').fetchone():
        return
    conn.execute("ALTER TABLE agent_runs ADD COLUMN config TEXT NOT NULL DEFAULT 'D'")
    conn.execute("UPDATE agent_runs SET config='A' WHERE gateway='off'")
    conn.execute('INSERT INTO schema_migrations VALUES (14,?)', (stamp,))
