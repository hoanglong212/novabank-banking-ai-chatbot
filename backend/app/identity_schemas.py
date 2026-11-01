import re
import unicodedata
from pydantic import BaseModel, ConfigDict, Field, field_validator


class IdentityInput(BaseModel):
    model_config = ConfigDict(extra='forbid', strict=True)


class EmailInput(IdentityInput):
    email: str = Field(max_length=254)

    @field_validator('email')
    @classmethod
    def normalize_email(cls, value):
        value = value.strip().lower()
        # Deliberately bounded demo format, with no email-validator dependency.
        if not re.fullmatch(r"[a-z0-9.!#$%&'*+/=?^_`{|}~-]{1,64}@[a-z0-9](?:[a-z0-9.-]*[a-z0-9])?\.[a-z]{2,63}", value):
            raise ValueError('Invalid email')
        return value


class PasswordInput(IdentityInput):
    password: str = Field(min_length=15, max_length=128)


class RegisterInput(EmailInput, PasswordInput):
    username: str = Field(max_length=64)
    name: str = Field(max_length=80)

    @field_validator('username')
    @classmethod
    def normalize_username(cls, value):
        value = value.strip().lower()
        if not re.fullmatch(r'[a-z][a-z0-9_]{2,31}', value):
            raise ValueError('Invalid username')
        return value

    @field_validator('name')
    @classmethod
    def validate_name(cls, value):
        value = value.strip()
        if len(value) < 2 or any(unicodedata.category(c).startswith('C') for c in value):
            raise ValueError('Invalid display name')
        return value


class TokenInput(IdentityInput):
    token: str = Field(min_length=43, max_length=43, pattern=r'^[A-Za-z0-9_-]+$')


class ResetInput(TokenInput, PasswordInput):
    pass
