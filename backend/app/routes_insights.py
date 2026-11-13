from datetime import date
from typing import Literal
import uuid
from fastapi import APIRouter, Depends, HTTPException, Query, Response
from pydantic import Field
from . import insights
from .dependencies import customer_user, get_db
from .identity import transaction
from .identity_schemas import IdentityInput
from .products import owned

router = APIRouter(prefix='/api', dependencies=[Depends(customer_user)])


class Budget(IdentityInput):
    month: str = Field(pattern=r'^\d{4}-\d{2}$')
    category: str = Field(max_length=30)
    amount_vnd: int = Field(ge=1000, le=1000000000)


class Goal(IdentityInput):
    label: str = Field(min_length=1, max_length=80)
    target_vnd: int = Field(ge=1000, le=1000000000)
    target_date: str = Field(pattern=r'^\d{4}-\d{2}-\d{2}$')
    savings_id: str | None = Field(default=None, max_length=100)


@router.get('/insights')
def summary(month: str = Query(pattern=r'^\d{4}-\d{2}$'), user=Depends(customer_user), db=Depends(get_db)):
    return insights.summary(db, user, month)


@router.put('/insights/budgets')
def budget(payload: Budget, user=Depends(customer_user), db=Depends(get_db)):
    return insights.set_budget(db, user, payload.month, payload.category, payload.amount_vnd)


@router.patch('/transactions/{transaction_id}/category')
def category(transaction_id: str, category: str = Query(max_length=30), user=Depends(customer_user), db=Depends(get_db)):
    if category not in insights.CATEGORIES:
        raise HTTPException(422, 'Unsupported category.')
    with transaction(db) as conn:
        if not conn.execute('SELECT 1 FROM transactions t JOIN accounts a ON a.id=t.account_id WHERE t.id=? AND a.owner_id=?', (transaction_id, user.id)).fetchone():
            raise HTTPException(404, 'Transaction not found.')
        conn.execute('INSERT INTO transaction_categories VALUES (?,?) ON CONFLICT(transaction_id) DO UPDATE SET category=excluded.category', (transaction_id, category))
    return {'message': 'Category updated.'}


@router.get('/statements.{fmt}')
def statement(fmt: Literal['csv', 'pdf'], from_date: date, to_date: date, user=Depends(customer_user), db=Depends(get_db)):
    data = insights.statement(db, user, from_date, to_date, fmt)
    return Response(data, media_type='text/csv' if fmt == 'csv' else 'application/pdf', headers={
        'Content-Disposition': f'attachment; filename="NovaBank-statement-{from_date}-{to_date}.{fmt}"', 'Cache-Control': 'no-store'})


@router.get('/savings-goals')
def goals(user=Depends(customer_user), db=Depends(get_db)):
    with db.connect() as conn:
        return {'items': [dict(r) for r in conn.execute('''SELECT g.*,CASE WHEN s.status='ACTIVE' THEN s.principal_vnd ELSE 0 END AS saved_vnd
            FROM savings_goals g LEFT JOIN savings s ON s.id=g.savings_id WHERE g.owner_id=? ORDER BY g.target_date,g.id''', (user.id,))]}


@router.post('/savings-goals', status_code=201)
def create_goal(payload: Goal, user=Depends(customer_user), db=Depends(get_db)):
    return save_goal(payload, user, db)


@router.put('/savings-goals/{goal_id}')
def update_goal(goal_id: str, payload: Goal, user=Depends(customer_user), db=Depends(get_db)):
    return save_goal(payload, user, db, goal_id)


def save_goal(payload, user, db, goal_id=None):
    try:
        date.fromisoformat(payload.target_date)
    except ValueError:
        raise HTTPException(422, 'Choose a valid target date.')
    with transaction(db) as conn:
        if not payload.label.strip():
            raise HTTPException(422, 'Enter a goal name.')
        if goal_id:
            owned(conn, 'savings_goals', goal_id, user.id)
        if payload.savings_id:
            saving = owned(conn, 'savings', payload.savings_id, user.id)
            if saving['status'] != 'ACTIVE':
                raise HTTPException(409, 'Link an active savings account.')
        if goal_id:
            conn.execute('UPDATE savings_goals SET label=?,target_vnd=?,target_date=?,savings_id=? WHERE id=? AND owner_id=?',
                         (payload.label.strip(), payload.target_vnd, payload.target_date, payload.savings_id, goal_id, user.id))
        else:
            goal_id = uuid.uuid4().hex
            conn.execute('INSERT INTO savings_goals VALUES (?,?,?,?,?,?)', (goal_id, user.id, payload.label.strip(), payload.target_vnd, payload.target_date, payload.savings_id))
    return {'id': goal_id, 'message': 'Goal saved.'}


@router.delete('/savings-goals/{goal_id}')
def delete_goal(goal_id: str, user=Depends(customer_user), db=Depends(get_db)):
    with transaction(db) as conn:
        if not conn.execute('DELETE FROM savings_goals WHERE id=? AND owner_id=?', (goal_id, user.id)).rowcount:
            raise HTTPException(404, 'Goal not found.')
    return {'message': 'Goal removed.'}


@router.patch('/bills/{bill_id}/saved')
def save_bill(bill_id: str, saved: bool, user=Depends(customer_user), db=Depends(get_db)):
    with transaction(db) as conn:
        owned(conn, 'bills', bill_id, user.id)
        conn.execute('UPDATE bills SET saved=? WHERE id=?', (int(saved), bill_id))
    return {'message': 'Bill preference saved.'}
