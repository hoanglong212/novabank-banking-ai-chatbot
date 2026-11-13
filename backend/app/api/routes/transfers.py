from fastapi import APIRouter, Depends, HTTPException, Header
from ... import transfers, vietqr
from ...auth import DemoPrincipal
from ...config import provider, setting
from ...database import Database
from ...dependencies import get_db, current_user, customer_user, assistant_user
from ...schemas import ConversationCreate, SendMessage, DemoToolCheck, TransferArgs, TransferConfirm, VietQRArgs
from ...agent import make_agent
from ...gateway import PolicyGateway
from ...guard import inspect_prompt
from ...tools import ToolDispatcher

router = APIRouter()

def transfer_failed(exc: transfers.TransferError) -> HTTPException:
    status = {'TRANSFER_NOT_FOUND': 404, 'VIETQR_UNAVAILABLE': 502, 'IDEMPOTENCY_CONFLICT': 409,
              'POSTING_FAILED': 503, 'LEDGER_MISMATCH': 503, 'PIN_REQUIRED': 403, 'PIN_LOCKED': 423,
              'TOKEN_REQUIRED': 403, 'TOKEN_INVALID': 403, 'TOKEN_EXPIRED': 403, 'TOKEN_MISMATCH': 403, 'TOKEN_REPLAYED': 409}.get(exc.reason_code, 400)
    return HTTPException(status_code=status, detail=exc.reason_code)


def with_token(draft: dict) -> dict:
    """Public view plus a fresh confirmation token while the owner can still confirm it (B5)."""
    result = transfers.public(draft)
    if draft['status'] == 'PENDING_OTP' and not draft.get('settlement_status'):
        from ...transfer_token import issue
        result['confirm_token'] = issue(draft, transfers._expires_at(draft), transfers.now())
    return result


@router.post('/api/transfers', status_code=201)
async def create_transfer(payload: TransferArgs, user: DemoPrincipal = Depends(customer_user)):
    db = get_db()
    try:
        draft = await transfers.prepare(db, user, payload.model_dump(exclude_none=True))
        draft, _ = transfers.issue_otp(db, user, draft['id'])
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc
    return with_token(draft)


@router.post('/api/transfers/{transfer_id}/otp')
async def resend_transfer_otp(transfer_id: str, user: DemoPrincipal = Depends(customer_user)):
    try:
        draft, _ = transfers.issue_otp(get_db(), user, transfer_id)
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc
    return with_token(draft)


@router.get('/api/transfers/{transfer_id}')
def transfer_status(transfer_id: str, user: DemoPrincipal = Depends(customer_user)):
    try:
        with get_db().connect() as conn:
            draft = transfers._own_transfer(conn, transfer_id, user)
            result = with_token(draft)
            if draft['transaction_id']:
                row = conn.execute('SELECT balance_after_vnd FROM transaction_details WHERE transaction_id=?', (draft['transaction_id'],)).fetchone()
                if row:
                    result['balance_vnd'] = row[0]
            return result
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc


@router.post('/api/transfers/{transfer_id}/confirm')
def confirm_transfer(transfer_id: str, payload: TransferConfirm, user: DemoPrincipal = Depends(customer_user),
                     idempotency_key: str | None = Header(default=None, min_length=1, max_length=128,
                                                         pattern=r'^[A-Za-z0-9._:-]+$')):
    try:
        return transfers.confirm(get_db(), user, transfer_id, payload.otp, idempotency_key, payload.confirm_token)
    except transfers.TransferError as exc:
        raise transfer_failed(exc) from exc


@router.get('/api/vietqr/banks')
async def vietqr_banks(user: DemoPrincipal = Depends(customer_user)):
    try:
        return [{k: b.get(k) for k in ('bin', 'code', 'shortName', 'name', 'logo')} for b in await vietqr.banks()]
    except vietqr.VietQRError as exc:
        raise HTTPException(status_code=502, detail='VietQR bank list is unavailable') from exc


@router.post('/api/vietqr')
async def create_vietqr(payload: VietQRArgs, user: DemoPrincipal = Depends(customer_user)):
    try:
        return await vietqr.generate(**payload.model_dump(exclude_none=True))
    except vietqr.VietQRError as exc:
        raise HTTPException(status_code=400 if exc.reason_code == 'UNKNOWN_BANK' else 502, detail=exc.reason_code) from exc


