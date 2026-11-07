"""Money rules: integer cents and GST.

Every amount in the system is an integer number of Singapore cents. Nothing
here uses a float, because a float cannot represent 0.10 exactly and money must
balance to the cent.

GST is 9% from 1 January 2024 (IRAS). A quote states whether its total already
contains GST, so the printed figures never guess.
"""

from __future__ import annotations

GST_RATE_BP: int = 900
"""Nine percent, in basis points of one hundredth of a percent."""

MAX_AMOUNT_CENTS: int = 100_000_000
"""One million Singapore dollars, the ceiling for one quote."""


def gst_component(amount_cents: int, rate_bp: int = GST_RATE_BP, included: bool = False) -> int:
    """Return the GST part of ``amount_cents``, rounded half up."""
    if amount_cents < 0:
        raise ValueError("An amount must not be negative")
    if rate_bp < 0:
        raise ValueError("A tax rate must not be negative")
    if included:
        divisor = 10_000 + rate_bp
        return (amount_cents * rate_bp + divisor // 2) // divisor
    return (amount_cents * rate_bp + 5_000) // 10_000


def grand_total(amount_cents: int, rate_bp: int = GST_RATE_BP, included: bool = False) -> int:
    """Return the amount a customer pays, GST added when it is not included."""
    if included:
        return amount_cents
    return amount_cents + gst_component(amount_cents, rate_bp, included=False)


def format_cents(amount_cents: int) -> str:
    """Return ``S$1,234.56`` for ``123456``."""
    sign = "-" if amount_cents < 0 else ""
    whole, cents = divmod(abs(amount_cents), 100)
    return f"{sign}S${whole:,}.{cents:02d}"