from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=40)
    password: str = Field(min_length=1, max_length=128)


class ConversationCreate(BaseModel):
    title: str = Field(default='New conversation', min_length=1, max_length=100)


class SendMessage(BaseModel):
    content: str = Field(min_length=1, max_length=4000)


class DemoToolCheck(BaseModel):
    tool_name: str = Field(min_length=1, max_length=80)
    arguments: dict[str, Any] = Field(default_factory=dict)


class FaqArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    query: str = Field(min_length=2, max_length=400)


class BalanceArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    account_id: str | None = Field(default=None, max_length=40)


class TransactionArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    transaction_id: str = Field(min_length=3, max_length=40)


class RecentTransactionsArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    limit: int = Field(default=5, ge=1, le=20)


class TicketArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    subject: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=8, max_length=800)


class VietQRArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    bank: str = Field(min_length=2, max_length=40, description='Bank short name, code or BIN, e.g. Vietcombank, VCB, 970436')
    account_no: str = Field(pattern=r'^\d{6,19}$')
    amount_vnd: int | None = Field(default=None, gt=0, le=10_000_000_000)
    add_info: str | None = Field(default=None, max_length=80)
    account_name: str | None = Field(default=None, max_length=50)


class TransferArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    from_account: str | None = Field(default=None, max_length=40, description='Payer account; omit for the customer own account')
    to_bank: str = Field(default='NovaBank', min_length=2, max_length=40, description='NovaBank, or a bank short name/code/BIN')
    to_account: str = Field(pattern=r'^(?i:ACC-[A-Z0-9-]{3,30}|\d{6,19})$', description='NovaBank ID like ACC-BOB-001 or a bank account number')
    amount_vnd: int = Field(ge=1000, le=100_000_000)
    content: str | None = Field(default=None, max_length=80)
    to_name: str | None = Field(default=None, max_length=50)


class TransferConfirm(BaseModel):
    otp: str = Field(pattern=r'^\d{6}$')


class ToolDecision(BaseModel):
    decision: Literal['ALLOW', 'DENY']
    reason_code: str
