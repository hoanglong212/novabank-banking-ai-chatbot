"""Customer history/receipts/alerts and permission-checked financial operations views."""
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from .auth import DemoPrincipal
from .banking_queries import TransactionQuery, notifications, transaction, transactions
from .database import now
from .dependencies import customer_user, get_db, require_permission
from .receipts import receipt_pdf

router = APIRouter(prefix='/api')
notifications_user = require_permission('notifications:own')
transactions_reader = require_permission('admin:transactions:read')
audit_reader = require_permission('admin:audit:read')


@router.get('/transactions')
def customer_transactions(query: TransactionQuery = Depends(), user: DemoPrincipal = Depends(customer_user)):
    return transactions(get_db(), query, user.id)


@router.get('/transactions/{transaction_id}')
def customer_transaction(transaction_id: str, user: DemoPrincipal = Depends(customer_user)):
    return transaction(get_db(), transaction_id, user.id)


@router.get('/transactions/{transaction_id}/receipt.pdf')
def download_receipt(transaction_id: str, user: DemoPrincipal = Depends(customer_user)):
    tx = transaction(get_db(), transaction_id, user.id)
    if tx['status'] != 'COMPLETED':
        raise HTTPException(409, 'A receipt is available only for completed transactions')
    # Filename contains a fixed prefix and an identifier created by the application.
    safe_id = ''.join(c for c in transaction_id if c.isascii() and (c.isalnum() or c == '-'))[:80]
    return Response(receipt_pdf(tx), media_type='application/pdf', headers={
        'Content-Disposition': f'attachment; filename="NovaBank-{safe_id}.pdf"', 'Cache-Control': 'no-store'})


@router.get('/notifications')
def list_notifications(user: DemoPrincipal = Depends(notifications_user),
                       limit: int = Query(default=20, ge=1, le=100), offset: int = Query(default=0, ge=0)):
    return notifications(get_db(), user.id, limit, offset)


@router.patch('/notifications/{notification_id}/read')
def mark_notification_read(notification_id: str, user: DemoPrincipal = Depends(notifications_user)):
    with get_db().connect() as conn:
        for table in ('notifications', 'service_notifications'):
            changed = conn.execute(f'UPDATE {table} SET read_at=COALESCE(read_at,?) WHERE id=? AND owner_id=?',
                                   (now(), notification_id, user.id))
            if changed.rowcount:
                return dict(conn.execute(f'SELECT * FROM {table} WHERE id=? AND owner_id=?', (notification_id, user.id)).fetchone())
        raise HTTPException(404, 'Notification not found')


@router.post('/notifications/read-all')
def mark_all_notifications_read(user: DemoPrincipal = Depends(notifications_user)):
    with get_db().connect() as conn:
        count = 0
        for table in ('notifications', 'service_notifications'):
            count += conn.execute(f'UPDATE {table} SET read_at=? WHERE owner_id=? AND read_at IS NULL', (now(), user.id)).rowcount
        return {'updated': count}


@router.get('/admin/transactions')
def admin_transactions(query: TransactionQuery = Depends(), user: DemoPrincipal = Depends(transactions_reader)):
    return transactions(get_db(), query, None)


@router.get('/admin/transfers/{transfer_id}/audit')
def transfer_audit(transfer_id: str, user: DemoPrincipal = Depends(audit_reader)):
    with get_db().connect() as conn:
        if conn.execute('SELECT 1 FROM transfers WHERE id=?', (transfer_id,)).fetchone() is None:
            raise HTTPException(404, 'Transfer not found')
        rows = conn.execute('SELECT * FROM banking_audit WHERE resource_id=? ORDER BY created_at,rowid', (transfer_id,)).fetchall()
        return {'items': [dict(row) for row in rows]}
