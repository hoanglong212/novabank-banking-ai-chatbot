"""Fictional sample knowledge base; no real-bank fees or policy statements."""
import re
import unicodedata

FAQ = [
    ('account', 'Opening an account', 'Check your bank\'s official channels for its account-opening process. NovaBank is fictional and cannot open real accounts.', ['mo tai khoan', 'open account', 'open an account', 'dang ky tai khoan']),
    ('card', 'Blocked card', 'If your card is blocked, contact the issuing bank through its official helpline or visit a branch for verification. This demo cannot unlock real cards.', ['the bi khoa', 'khoa the', 'atm', 'card blocked', 'blocked card']),
    ('vietqr', 'VietQR', 'VietQR presents payment or transfer details in a QR code. Always verify the recipient, amount, and bank in your official banking app before approving a transfer.', ['vietqr', 'qr', 'ma qr', 'quet ma']),
    ('transfer', 'Bank transfers', 'Check the recipient, limits, and transaction status in your official banking app. Fees and limits depend on your bank and account type.', ['chuyen tien', 'chuyen khoan', 'transfer', 'han muc', 'phi chuyen', 'fees', 'limits']),
    ('fraud', 'Fraud prevention', 'Never share passwords, OTPs, PINs, or recovery codes with a chatbot or strangers. If you suspect fraud, contact your bank through its official channels.', ['lua dao', 'otp', 'pin', 'bao mat', 'mat tien', 'fraud', 'scam', 'security']),
    ('hours', 'Opening hours', 'Opening hours vary by bank and branch. Check your bank\'s official website for current hours.', ['gio lam viec', 'chi nhanh', 'branch', 'working hours', 'opening hours']),
    ('transaction', 'Delayed transactions', 'If a transfer has not arrived, save its reference number, check its status in your banking app, and contact official support. This app only contains simulated transactions.', ['giao dich loi', 'chua nhan', 'pending', 'giao dich', 'cham tien', 'delayed', 'not arrived']),
]


def fold(s: str) -> str:
    s = s.lower().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def search(query: str):
    words = [w for w in re.findall(r'\w+', fold(query)) if len(w) > 2]
    found = []
    for key, title, answer, synonyms in FAQ:
        bag = fold(' '.join([key, title, *synonyms]))
        score = sum(1 for w in words if w in bag)
        if any(fold(synonym) in fold(query) for synonym in synonyms):
            score += 3
        if score:
            found.append((score, key, title, answer))
    found.sort(key=lambda x: x[0], reverse=True)
    if not found:
        return {'matches': [], 'notice': 'No approved sample-bank FAQ answer found. Do not invent a fee, limit or bank rule.'}
    return {'matches': [{'id': k, 'title': t, 'answer': a} for _, k, t, a in found[:2]], 'notice': 'All NovaBank FAQ data is fictional demonstration material.'}
