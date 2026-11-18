"""Bank-owned conversation receipts and follow-up reads for transfer status."""
import re
import uuid

from .faq import fold


APPROVED_DRAFT = """FROM tool_approvals a JOIN agent_runs r ON r.id=a.run_id
    JOIN transfers t ON t.owner_id=a.owner_id AND t.id=json_extract(a.response_json,'$.draft_id')
    LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
    WHERE a.name='prepare_transfer' AND a.status='APPROVED' AND a.owner_id=? AND r.owner_id=a.owner_id"""

FOLLOWUP = re.compile(
    r'^(?:did (?:it|the transfer|my transfer|the payment) (?:go through|complete|succeed)'
    r'|(?:has|is) (?:my |the |that )?(?:last |latest |recent )?(?:transfer|payment) (?:completed?|successful|pending)'
    r'|(?:what is |check )?(?:the )?status of (?:my |the |that )?(?:last |latest |recent )?(?:transfer|payment)'
    r'|(?:(?:toi |da |vua )*(?:chuyen tien|chuyen khoan)|giao dich(?: vua roi| nay| do)?)'
    r'(?: (?:da|cua toi|vua roi))* (?:xong|thanh cong|hoan tat|hoan thanh|thuc hien) chua'
    r'|(?:kiem tra |xem )?trang thai (?:lan )?(?:chuyen tien|chuyen khoan|giao dich)(?: (?:vua roi|gan nhat|nay|do))?)[ ?.!]*$'
)


def status_text(status, amount, reference):
    state = {
        'COMPLETED': 'Transfer successful',
        'PENDING': 'Transfer pending',
        'FAILED': 'Transfer failed',
        'PENDING_OTP': 'Transfer awaiting bank confirmation',
    }[status]
    return f'{state} · {amount:,} VND' + (f' · {reference}' if reference else '') + '.'


def conversation_for(conn, owner, transfer_id):
    row = conn.execute('SELECT r.conversation_id ' + APPROVED_DRAFT + ' AND t.id=? LIMIT 1',
                       (owner, transfer_id)).fetchone()
    return row['conversation_id'] if row else None


def record(conn, transfer, status, reference, stamp):
    conversation_id = conversation_for(conn, transfer['owner_id'], transfer['id'])
    if not conversation_id:
        return
    content = status_text(status, transfer['amount_vnd'], reference)
    conn.execute("INSERT INTO messages VALUES (?,?,'assistant',?,?)",
                 (str(uuid.uuid4()), conversation_id, content, stamp))
    conn.execute('UPDATE conversations SET updated_at=? WHERE id=?', (stamp, conversation_id))


def followup(conn, owner, conversation, question):
    text = fold(question).strip()
    if not FOLLOWUP.fullmatch(text):
        return None
    if re.search(r'\b(?:last|latest|recent|gan nhat)\b', text):
        row = conn.execute('''SELECT t.amount_vnd,t.status,t.transaction_id,s.status AS settlement_status
            FROM transfers t LEFT JOIN interbank_settlements s ON s.transfer_id=t.id
            WHERE t.owner_id=? AND t.transaction_id IS NOT NULL
            ORDER BY t.completed_at DESC,t.rowid DESC LIMIT 1''', (owner,)).fetchone()
    else:
        row = conn.execute('SELECT t.amount_vnd,t.status,t.transaction_id,s.status AS settlement_status '
            + APPROVED_DRAFT + ' AND r.conversation_id=? ORDER BY t.created_at DESC,t.rowid DESC LIMIT 1',
            (owner, conversation)).fetchone()
    if row:
        return status_text(row['settlement_status'] or row['status'], row['amount_vnd'], row['transaction_id'])
    return 'Open Activity to check the transfer or give me its TX reference.'
