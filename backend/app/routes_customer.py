from typing import Literal
from fastapi import APIRouter, Depends, Header, Query, Response
from pydantic import Field
from . import action_security, customer_services, products
from .dependencies import current_user, customer_user, get_db
from .identity_schemas import IdentityInput


def no_cache(response: Response):
    response.headers['Cache-Control'] = 'no-store'


router = APIRouter(prefix='/api', dependencies=[Depends(no_cache)])


class ProfileChange(IdentityInput):
    field: Literal['name', 'email', 'phone', 'password']
    value: str = Field(min_length=1, max_length=254)
    password: str = Field(min_length=1, max_length=128)


class Nickname(IdentityInput):
    nickname: str = Field(min_length=1, max_length=80)


class NotificationPreferences(IdentityInput):
    bill_reminders: bool
    budget_alerts: bool


@router.get('/customer/notification-preferences')
def preferences(user=Depends(current_user), db=Depends(get_db)):
    from .notification_preferences import get
    return get(db, user.id)


@router.put('/customer/notification-preferences')
def update_preferences(payload: NotificationPreferences, user=Depends(current_user), db=Depends(get_db)):
    from .notification_preferences import save
    return save(db, user.id, **payload.model_dump())


class Beneficiary(Nickname):
    account_id: str = Field(min_length=3, max_length=40)
    bank: str = Field(min_length=2, max_length=80)


class RecipientLookup(IdentityInput):
    account_id: str = Field(min_length=3, max_length=40)
    bank: str = Field(min_length=2, max_length=80)


@router.post('/customer/beneficiaries/lookup')
async def lookup_recipient(payload: RecipientLookup, user=Depends(customer_user), db=Depends(get_db)):
    return await customer_services.lookup_recipient(db, user, **payload.model_dump())


class ActionConfirm(IdentityInput):
    challenge_id: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')
    code: str = Field(min_length=6, max_length=6, pattern=r'^[0-9]{6}$')


class ProductAction(IdentityInput):
    kind: Literal['PAY_BILL', 'OPEN_SAVINGS', 'WITHDRAW_SAVINGS', 'FREEZE_CARD', 'UNFREEZE_CARD', 'CARD_PURCHASE', 'REPAY_CARD']
    resource_id: str | None = Field(default=None, min_length=1, max_length=100)
    account_id: str | None = Field(default=None, min_length=1, max_length=100)
    amount_vnd: int | None = Field(default=None, ge=1000, le=100000000)
    term_months: int | None = Field(default=None, ge=1, le=12)
    label: str = Field(default='', max_length=120)


@router.get('/customer/profile')
def profile(user=Depends(current_user), db=Depends(get_db)):
    return customer_services.profile(db, user)


@router.post('/customer/profile/change', status_code=202)
def profile_change(payload: ProfileChange, user=Depends(current_user), db=Depends(get_db)):
    return customer_services.change_profile(db, user, **payload.model_dump())


@router.get('/customer/accounts')
def accounts(user=Depends(customer_user), db=Depends(get_db)):
    return customer_services.accounts(db, user)


@router.patch('/customer/accounts/{account_id}')
def account_label(account_id: str, payload: Nickname, user=Depends(customer_user), db=Depends(get_db)):
    return customer_services.account_label(db, user, account_id, payload.nickname)


@router.get('/customer/beneficiaries')
def beneficiaries(q: str = Query(default='', max_length=100), user=Depends(customer_user), db=Depends(get_db)):
    return customer_services.beneficiaries(db, user, q)


@router.patch('/customer/beneficiaries/{beneficiary_id}')
def edit_beneficiary(beneficiary_id: str, payload: Nickname, user=Depends(customer_user), db=Depends(get_db)):
    return customer_services.edit_beneficiary(db, user, beneficiary_id, payload.nickname)


@router.post('/customer/beneficiaries', status_code=201)
async def beneficiary(payload: Beneficiary, user=Depends(customer_user), db=Depends(get_db)):
    return await customer_services.save_beneficiary(db, user, **payload.model_dump())


@router.delete('/customer/beneficiaries/{beneficiary_id}')
def remove_beneficiary(beneficiary_id: str, user=Depends(customer_user), db=Depends(get_db)):
    return customer_services.delete_beneficiary(db, user, beneficiary_id)


@router.post('/actions/confirm')
def confirm(payload: ActionConfirm, user=Depends(current_user), db=Depends(get_db),
            idempotency_key: str | None = Header(default=None, min_length=1, max_length=128, pattern=r'^[A-Za-z0-9._:-]+$')):
    return action_security.confirm(db, user, payload.challenge_id, payload.code, idempotency_key)


@router.get('/products/{kind}')
def product_list(kind: Literal['cards', 'bills', 'savings'], user=Depends(customer_user), db=Depends(get_db)):
    return products.list_products(db, user, kind)


@router.post('/products/actions', status_code=202)
def product_action(payload: ProductAction, user=Depends(customer_user), db=Depends(get_db)):
    data = payload.model_dump(exclude_none=True)
    return products.prepare(db, user, data.pop('kind'), data)
