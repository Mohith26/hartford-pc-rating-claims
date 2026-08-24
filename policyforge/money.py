"""Integer cents arithmetic helpers.

Everything in this project is integer cents. Factors are integers scaled by
1000 (per mille). The only rounding rule anywhere is round half up, applied
through round_half_up_div so there is never any float in the money path.
"""


def round_half_up_div(numerator: int, denominator: int) -> int:
    """Divide two non negative integers, rounding half up.

    round_half_up_div(12112500, 1000) == 12113 because the remainder 500
    is exactly half of 1000 and half rounds up.
    """
    if numerator < 0 or denominator <= 0:
        raise ValueError("round_half_up_div expects numerator >= 0 and denominator > 0")
    q, r = divmod(numerator, denominator)
    if 2 * r >= denominator:
        q += 1
    return q


def apply_factor(cents: int, factor_milli: int) -> int:
    """Apply a per mille factor to a cents amount, rounding half up to a cent."""
    if cents < 0:
        raise ValueError("cents must be >= 0")
    if factor_milli < 0:
        raise ValueError("factor_milli must be >= 0")
    return round_half_up_div(cents * factor_milli, 1000)


def fmt_cents(cents: int) -> str:
    """Format integer cents as a dollar string, e.g. 158611 -> $1586.11."""
    sign = "-" if cents < 0 else ""
    cents = abs(cents)
    return "{}${}.{:02d}".format(sign, cents // 100, cents % 100)
