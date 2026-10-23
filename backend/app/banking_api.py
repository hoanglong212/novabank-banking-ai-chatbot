"""Authenticated banking API; all writes go through CSRF-protected sessions."""
import sqlite3
import unicodedata
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, ConfigDict, Field, StrictInt, field_validator
from .sessions import current_user, db
from .auth import DemoPrincipal
from .banking import accounts_for, transactions_for, create_intent, get_intent, confirm_transfer

router=APIRouter(prefix='/api')


class Preview(BaseModel):
    model_config=ConfigDict(extra='forbid')
    source_account_id: str=Field(min_length=1,max_length=40)
    recipient_account_id: str=Field(min_length=1,max_length=40)
    amount_vnd: StrictInt=Field(gt=0,le=1000000000000)
    description: str=Field(default='',max_length=140)

    @field_validator('description')
    @classmethod
    def plain_text(cls,value):
        if any(unicodedata.category(c) in ('Cc','Cf') for c in value):
            raise ValueError('Control characters are not allowed')
        return value.strip()


class Confirmation(BaseModel):
    model_config=ConfigDict(extra='forbid')


@router.get('/accounts')
def accounts(user: DemoPrincipal=Depends(current_user)):
    return accounts_for(db(),user.id)


@router.get('/transactions')
def history(user: DemoPrincipal=Depends(current_user)):
    return transactions_for(db(),user.id)


@router.get('/transactions/{transaction_id}')
def transaction(transaction_id: str,user: DemoPrincipal=Depends(current_user)):
    results=transactions_for(db(),user.id,transaction_id)
    if not results:
        raise HTTPException(404,'Transaction not found')
    return results[0]


@router.post('/transfers/intents',status_code=201)
def preview(payload: Preview,user: DemoPrincipal=Depends(current_user)):
    return create_intent(db(),user.id,payload.source_account_id,payload.recipient_account_id,payload.amount_vnd,payload.description)


@router.get('/transfers/intents/{intent_id}')
def intent(intent_id: str,user: DemoPrincipal=Depends(current_user)):
    return get_intent(db(),user.id,intent_id)


@router.post('/transfers/intents/{intent_id}/confirm')
def confirm(intent_id: str,payload: Confirmation,user: DemoPrincipal=Depends(current_user)):
    try:
        return confirm_transfer(db(),user.id,intent_id)
    except sqlite3.OperationalError as exc:
        if 'locked' in str(exc).lower() or 'busy' in str(exc).lower():
            raise HTTPException(503,'Database busy; retry the same preview',headers={'Retry-After':'1'}) from None
        raise


@router.post('/transfers/intents/{intent_id}/cancel')
def cancel(intent_id: str,payload: Confirmation,user: DemoPrincipal=Depends(current_user)):
    with db().connect() as conn:
        conn.execute('BEGIN IMMEDIATE')
        row=conn.execute('SELECT status FROM transfer_intents WHERE id=? AND owner_id=?',(intent_id,user.id)).fetchone()
        if not row:
            raise HTTPException(404,'Transfer preview not found')
        if row['status']=='completed':
            raise HTTPException(409,'Transfer already completed; view history')
        conn.execute("UPDATE transfer_intents SET status='cancelled' WHERE id=?",(intent_id,))
    return {'cancelled':True}
