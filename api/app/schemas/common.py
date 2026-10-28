from datetime import date
from decimal import Decimal
from typing import Annotated, Self

from pydantic import BaseModel, ConfigDict, Field, StringConstraints, model_validator

EMAIL_PATTERN = r"^[^@\s]+@[^@\s]+\.[^@\s]+$"

Email = Annotated[
    str,
    StringConstraints(strip_whitespace=True, to_lower=True, max_length=254, pattern=EMAIL_PATTERN),
]
Name = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=200)]
Money = Annotated[Decimal, Field(ge=0, max_digits=12, decimal_places=2)]
SearchText = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


class InputModel(BaseModel):
    """Request bodies: unknown fields are rejected, so clients can't set fields we don't expose."""

    model_config = ConfigDict(extra="forbid")


class PatchModel(InputModel):
    """Partial update: omitted fields stay unchanged; explicit nulls are rejected."""

    @model_validator(mode="after")
    def _no_nulls(self) -> Self:
        nulls = [name for name in self.model_fields_set if getattr(self, name) is None]
        if nulls:
            raise ValueError(f"Fields can't be null: {', '.join(sorted(nulls))}")
        return self

    def changes(self) -> dict[str, object]:
        return self.model_dump(exclude_unset=True)


class OutputModel(BaseModel):
    model_config = ConfigDict(from_attributes=True)


class PageParams(InputModel):
    page: int = Field(1, ge=1, le=10_000)
    page_size: int = Field(25, ge=1, le=100)

    @property
    def offset(self) -> int:
        return (self.page - 1) * self.page_size


class DateRange(InputModel):
    date_from: date | None = None
    date_to: date | None = None  # inclusive

    @model_validator(mode="after")
    def _ordered(self) -> Self:
        if self.date_from and self.date_to and self.date_from > self.date_to:
            raise ValueError("date_from must be on or before date_to")
        return self


class Page[T](BaseModel):
    items: list[T]
    total: int
    page: int
    page_size: int
