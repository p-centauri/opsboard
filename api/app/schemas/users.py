from datetime import datetime

from pydantic import Field

from app.models import Role
from app.schemas.common import Email, InputModel, OutputModel


class LoginIn(InputModel):
    email: Email
    password: str = Field(min_length=1, max_length=256)


class UserOut(OutputModel):
    id: int
    email: str
    role: Role
    is_active: bool
    created_at: datetime


class UserUpdate(InputModel):
    role: Role | None = None
    is_active: bool | None = None
