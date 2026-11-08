"""Commander domain state models."""

from __future__ import annotations

from dataclasses import dataclass

from ..exceptions import DomainValidationError


@dataclass(frozen=True, slots=True)
class CommanderState:
    """Commander profile, credit balance, loan status, and criminal reputation."""

    name: str | None = None
    fid: str | None = None
    credits: int = 0
    loan: int = 0
    is_wanted: bool = False

    def __post_init__(self) -> None:
        """Validates credit balance and loan amounts."""
        if self.credits < 0:
            raise DomainValidationError("Credits balance cannot be negative.")
        if self.loan < 0:
            raise DomainValidationError("Loan balance cannot be negative.")
