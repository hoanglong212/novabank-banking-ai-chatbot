"""Input guard: runs on every prompt before it is stored or reaches an agent.

1. Secrets (card numbers, OTP/PIN/CVV, passwords) are redacted and the turn is refused.
2. Prompt-injection / jailbreak attempts are refused.
3. Pseudonymizer swaps PII for reversible tokens so the LLM never sees real values;
   tools receive the restored values only after policy authorization.
"""
import re
from dataclasses import dataclass
from .faq import fold

CARD = re.compile(r'(?<!\d)(?:\d[ -]?){15,18}\d(?!\d)')
SECRET = re.compile(
    r'\b(?:otp|pin|cvv|cvc|m[aã]\s*x[aá]c\s*(?:th[uự]c|nh[aậ]n))\b[\s:=]*(?:is|l[aà])?[\s:=]*\d{3,8}\b'
    r'|\b(?:password|passcode|m[aậ]t\s*kh[aẩ]u)\b\s*(?:is|l[aà]|:|=)\s*\S+', re.I)
INJECTION = re.compile(
    r'ignore (?:all |any |the )?(?:previous|prior|above|earlier|your) (?:instructions|rules|prompts?)'
    r'|(?:bo qua|phot lo) (?:moi |tat ca |cac )?(?:huong dan|chi dan|quy tac|lenh)'
    r'|system prompt|developer mode|jailbreak|\bdan mode\b|you are now\b'
    r'|act as (?:an? )?(?:admin|administrator|developer|root)|ban bay gio la|gia vo (?:la|lam)')

# Order matters: keyword-anchored patterns first, so "account 012345678901" is not taken for an ID.
PII = (
    ('EMAIL', re.compile(r'[\w.+-]+@[\w-]+\.[\w.-]+')),
    # Only digits introduced as an account, so amounts like 500000 stay readable for the model.
    ('ACCOUNT', re.compile(r'(?i:\bstk|s[oố]\s*t[aà]i\s*kho[aả]n|t[aà]i\s*kho[aả]n|account(?:\s*(?:no|number))?)\s*[:#]?\s*(\d{6,19})\b')),
    # VietQR account names are upper case without diacritics.
    ('NAME', re.compile(r'(?i:\bt[eê]n|account name|ch[uủ] t[aà]i kho[aả]n)\s*:?\s*([A-Z]{2,}(?: [A-Z]{1,})+)')),
    ('PHONE', re.compile(r'(?<!\d)(?:\+84|84|0)[35789]\d{8}(?!\d)')),
    ('NATIONAL_ID', re.compile(r'(?<!\d)\d{12}(?!\d)')),
)
TOKEN = re.compile(r'<(?:EMAIL|PHONE|NATIONAL_ID|ACCOUNT|NAME)_\d+>')


def luhn(digits: str) -> bool:
    total = 0
    for i, d in enumerate(reversed(digits)):
        n = int(d) * (2 if i % 2 else 1)
        total += n - 9 if n > 9 else n
    return total % 10 == 0


def redact_secrets(text: str) -> tuple[str, bool]:
    def card(m):
        digits = re.sub(r'\D', '', m.group())
        # shortcut: 16/19-digit Luhn only (Visa/Mastercard/NAPAS); 15-digit Amex is not caught.
        return '[REDACTED CARD]' if len(digits) in (16, 19) and luhn(digits) else m.group()
    clean = SECRET.sub('[REDACTED SECRET]', CARD.sub(card, text))
    return clean, clean != text


@dataclass
class Verdict:
    text: str
    reason: str | None = None
    reply: str | None = None


def inspect_prompt(text: str) -> Verdict:
    clean, had_secret = redact_secrets(text)
    if had_secret:
        return Verdict(clean, 'SECRET_REDACTED',
                       'I removed sensitive data (card number, OTP, PIN or password) from your message and did not process it. '
                       'Never share these with anyone, including Nova.')
    if INJECTION.search(fold(clean)):
        return Verdict(clean, 'PROMPT_INJECTION',
                       'This request tries to change my safety instructions, so I cannot process it. '
                       'Please ask a banking question instead.')
    return Verdict(clean)


class Pseudonymizer:
    """Per-request reversible vault; tokens are stable within one request."""

    def __init__(self):
        self.real: dict[str, str] = {}
        self.token: dict[str, str] = {}

    def _swap(self, kind: str, value: str) -> str:
        if value not in self.token:
            n = sum(1 for t in self.real if t.startswith(f'<{kind}_')) + 1
            self.token[value] = f'<{kind}_{n}>'
            self.real[self.token[value]] = value
        return self.token[value]

    def pseudonymize(self, text: str) -> str:
        for kind, pattern in PII:
            if pattern.groups:
                text = pattern.sub(lambda m: m.group()[:m.start(1) - m.start()] + self._swap(kind, m.group(1)), text)
            else:
                text = pattern.sub(lambda m: self._swap(kind, m.group()), text)
        return text

    def restore(self, value):
        if isinstance(value, str):
            return TOKEN.sub(lambda m: self.real.get(m.group(), m.group()), value)
        if isinstance(value, dict):
            return {k: self.restore(v) for k, v in value.items()}
        return value


def mask(value):
    """Audit-log masking: keep the last 4 digits of long numbers, hide email local parts."""
    if isinstance(value, str):
        value = re.sub(r'\d{8,}', lambda m: '*' * (len(m.group()) - 4) + m.group()[-4:], value)
        return re.sub(r'([\w.+-])[\w.+-]*@', r'\1***@', value)
    if isinstance(value, dict):
        return {k: mask(v) for k, v in value.items()}
    return value
