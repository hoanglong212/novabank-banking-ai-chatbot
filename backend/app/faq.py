"""Fictional sample knowledge base; no real-bank fees or policy statements."""
import re
import unicodedata

FAQ = [
    ('payments', 'How do I confirm a transfer from Assistant?',
     'Ask Nova to prepare a transfer with the amount and recipient account. Open Review transfer, check the details, '
     'then continue to bank verification. A new recipient requires a fresh authenticator code and a separate email code. '
     'Set your transaction PIN during this flow if you do not have one. Transfers to verified recipients use your PIN once it is set. '
     'The bank displays the final fee and debit before confirmation.',
     ['confirm a transfer', 'review transfer', 'new recipient', 'transfer verification', 'chuyen khoan', 'xem lai chuyen tien']),
    ('transaction', 'Where can I check a transfer or download a receipt?',
     'Open Activity and select the transaction to see its status and reference. Download the receipt after completion. '
     'For a transfer prepared in Assistant, its bank status appears in the conversation. Ask “Did the transfer go through?” there, '
     'or use the TX reference to check a specific transaction. A pending interbank transfer is still processing.',
     ['transfer status', 'track transfer', 'receipt', 'pending', 'giao dich', 'bien lai']),
    ('documents', 'How do I ask Nova about an uploaded file?',
     'In Assistant, open the paperclip or drop one text-based PDF, TXT, or Markdown file into the chat. '
     'Upload the file and wait for Ready, then choose Ask about document and enter a specific question. Nova cites the selected file. '
     'PDFs need selectable text. Files are limited to 5 MB and 50 pages.',
     ['uploaded file', 'pdf', 'documents', 'ask about document', 'rag', 'tai lieu']),
    ('qr-demo', 'Can I read a QR image in Assistant?',
     'Use Upload QR image or drop a PNG, JPEG, or WebP image in Assistant. Check the bank, account and amount in the preview '
     'before continuing to the bank verification screen. NovaBank simulator QR codes work within this demo.',
     ['qr image', 'upload qr', 'qr pay', 'ma qr', 'quet ma']),
    ('security', 'When do I use my authenticator or transaction PIN?',
     'Manage Authenticator and Transaction PIN in Profile, Security Center. The authenticator is used for sign-in when selected '
     'and is required for payments to a new recipient. A transaction PIN confirms later transfers to verified recipients. '
     'Enter codes or passwords only in the corresponding banking form.',
     ['transaction pin', 'authenticator', 'verification code', 'pin', 'otp', 'bao mat']),
    ('support', 'How do I get help with a transfer or my account?',
     'Open Explore, Help and support, then select New support request. Include the TX reference and what you saw. '
     'Track replies in the ticket. Keep passwords, codes and real banking information out of tickets and chat.',
     ['support request', 'help with a transfer', 'contact support', 'ho tro']),
    ('card', 'What can I do if my card is frozen?',
     'Open Explore, Cards and choose the card. Check its status, then use Unfreeze and complete bank verification if appropriate. '
     'If the card action is unavailable or you do not recognize recent activity, open a support request.',
     ['frozen card', 'card blocked', 'blocked card', 'khoa the']),
    ('vietqr', 'What should I check before paying a QR code?',
     'VietQR presents payment or transfer details in a QR code. Always verify the recipient, amount, and bank in your official banking app before approving a transfer.',
     ['vietqr', 'scan a qr']),
]


def fold(s: str) -> str:
    s = s.lower().replace('đ', 'd')
    return ''.join(c for c in unicodedata.normalize('NFD', s) if unicodedata.category(c) != 'Mn')


def exact_question(query):
    normalized = fold(query).strip().rstrip('?.!')
    return next((key for key, title, _, _ in FAQ if normalized == fold(title).rstrip('?.!')), None)


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
