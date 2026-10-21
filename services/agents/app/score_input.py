"""Read an optional publisher-supplied score without inventing a measurement."""
from __future__ import annotations

import math
from typing import Any


def supplied_risk_score(value: Any) -> float | None:
    """Preserve numeric zero; missing/invalid/nonfinite values stay unknown.

    A finite value is input, not proof of a vendor or a calibrated 0–1 scale.
    Numeric strings support existing historical connector rows.
    """
    if value is None or isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError, OverflowError):
        return None
    return number if math.isfinite(number) else None
