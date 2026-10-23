from typing import Any, Literal
from pydantic import BaseModel, Field, ConfigDict


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
    account_id: str | None = Field(default=None, min_length=1, max_length=40)


class TransactionArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    transaction_id: str = Field(min_length=3, max_length=40)


class TicketArgs(BaseModel):
    model_config = ConfigDict(extra='forbid')
    subject: str = Field(min_length=4, max_length=120)
    description: str = Field(min_length=8, max_length=800)


class ToolDecision(BaseModel):
    decision: Literal['ALLOW', 'DENY']
    reason_code: str
