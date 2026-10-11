"""Pagination envelope shared by every list endpoint.

``Page`` is generic so the frontend's table can be reused for orders, buyers,
vouchers and cases with one shape to parse.
"""


from __future__ import annotations

from typing import Generic, TypeVar

from pydantic import BaseModel, Field

T = TypeVar("T")


class Page(BaseModel, Generic[T]):
    """One page of a ledger query, with enough for the frontend to paginate."""

    items: list[T] = Field(default_factory=list)
    total: int = 0
    limit: int = 25
    offset: int = 0
    has_more: bool = False
