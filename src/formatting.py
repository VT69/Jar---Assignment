"""Number formatting helpers (Indian Rupee, Indian digit grouping, percentages)."""
from __future__ import annotations

import math


def indian_group(n: int) -> str:
    """Group an integer's digits the Indian way: 12,34,567.

    >>> indian_group(1234567)
    '12,34,567'
    """
    sign = "-" if n < 0 else ""
    s = str(abs(int(n)))
    if len(s) <= 3:
        return sign + s
    head, tail = s[:-3], s[-3:]
    pairs = []
    while len(head) > 2:
        pairs.insert(0, head[-2:])
        head = head[:-2]
    if head:
        pairs.insert(0, head)
    return sign + ",".join(pairs) + "," + tail


def inr(value: float, decimals: int = 0) -> str:
    """Format a rupee amount with Indian grouping, e.g. ``₹1,65,267`` or ``-₹1,148``.

    Args:
        value: Amount in rupees.
        decimals: Number of decimal places to keep.
    """
    if value is None or (isinstance(value, float) and math.isnan(value)):
        return "n/a"
    sign = "-" if value < 0 else ""
    value = abs(value)
    if decimals == 0:
        return f"{sign}₹{indian_group(int(round(value)))}"
    whole = int(value)
    frac = round(value - whole, decimals)
    if frac >= 1:  # rounding carried over
        whole, frac = whole + 1, 0.0
    frac_str = f"{frac:.{decimals}f}"[1:]  # '.xx'
    return f"{sign}₹{indian_group(whole)}{frac_str}"


def inr_compact(value: float) -> str:
    """Compact rupee label for axis ticks: ₹1.2L, ₹45K, ₹800."""
    sign = "-" if value < 0 else ""
    v = abs(value)
    if v >= 1e7:
        return f"{sign}₹{v / 1e7:.1f}Cr"
    if v >= 1e5:
        return f"{sign}₹{v / 1e5:.1f}L"
    if v >= 1e3:
        return f"{sign}₹{v / 1e3:.0f}K"
    return f"{sign}₹{v:.0f}"


def pct(value: float, decimals: int = 1, signed: bool = False) -> str:
    """Format a percentage that is already on the 0-100 scale."""
    fmt = f"{{:{'+' if signed else ''}.{decimals}f}}%"
    return fmt.format(value)


def pp(value: float, decimals: int = 1) -> str:
    """Format a signed percentage-point difference."""
    return f"{value:+.{decimals}f} pp"
