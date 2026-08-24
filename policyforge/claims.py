"""Claims settlement math, exact to the cent.

Every settlement function returns a result object with the payment plus the
intermediates, and each one keeps three hard invariants:

    1. indemnity is never negative
    2. indemnity never exceeds the applicable limit
    3. any deductible is applied exactly once

Documented settlement rules:

  * PD (property damage liability): pay min(loss, limit). No deductible.
  * COLL (collision): the insurer pays actual repair cost capped at the
    vehicle actual cash value, minus the deductible once, floored at zero:
    payment = max(0, min(loss, acv) - deductible).
  * BI (bodily injury liability): cap each claimant at the per person limit.
    If the capped total still exceeds the per occurrence limit, reduce
    pro rata in integer cents using the largest remainder method, breaking
    remainder ties by claimant index, so the payments sum to exactly the
    per occurrence limit.
  * RENT (rental reimbursement): pay min(daily rate, per day cap) per day,
    then cap the total at the aggregate limit.
  * Coinsurance (property style coverage): required = value x coinsurance
    percentage, rounded half up. If carried < required the loss is scaled by
    carried / required (rounded half up) before anything else. Then subtract
    the deductible once, floor at zero, cap at the carried limit. Order is
    fixed: coinsurance scaling, then deductible, then limit cap.
"""

from dataclasses import dataclass
from typing import List, Tuple

from .money import round_half_up_div


def _check_amount(name: str, value: int, allow_zero: bool = True) -> None:
    if value < 0 or (value == 0 and not allow_zero):
        raise ValueError("{} must be {} (got {})".format(
            name, ">= 0" if allow_zero else "> 0", value))


@dataclass
class PDSettlement:
    loss_cents: int
    limit_cents: int
    payment_cents: int


def settle_pd(loss_cents: int, limit_cents: int) -> PDSettlement:
    _check_amount("loss", loss_cents)
    _check_amount("limit", limit_cents, allow_zero=False)
    return PDSettlement(loss_cents, limit_cents, min(loss_cents, limit_cents))


@dataclass
class CollisionSettlement:
    loss_cents: int
    acv_cents: int
    deductible_cents: int
    covered_loss_cents: int  # loss capped at ACV, before deductible
    payment_cents: int


def settle_collision(loss_cents: int, acv_cents: int, deductible_cents: int) -> CollisionSettlement:
    _check_amount("loss", loss_cents)
    _check_amount("acv", acv_cents, allow_zero=False)
    _check_amount("deductible", deductible_cents)
    covered = min(loss_cents, acv_cents)
    payment = max(0, covered - deductible_cents)
    return CollisionSettlement(loss_cents, acv_cents, deductible_cents, covered, payment)


@dataclass
class BISettlement:
    losses_cents: Tuple[int, ...]
    per_person_cents: int
    per_occurrence_cents: int
    capped_cents: Tuple[int, ...]   # after per person caps, before occurrence cap
    payments_cents: Tuple[int, ...]

    @property
    def total_cents(self) -> int:
        return sum(self.payments_cents)


def settle_bi(losses_cents: List[int], per_person_cents: int, per_occurrence_cents: int) -> BISettlement:
    if not losses_cents:
        raise ValueError("at least one claimant loss is required")
    for loss in losses_cents:
        _check_amount("loss", loss)
    _check_amount("per person limit", per_person_cents, allow_zero=False)
    _check_amount("per occurrence limit", per_occurrence_cents, allow_zero=False)
    if per_occurrence_cents < per_person_cents:
        raise ValueError("per occurrence limit must be >= per person limit")

    capped = [min(loss, per_person_cents) for loss in losses_cents]
    total = sum(capped)
    if total <= per_occurrence_cents:
        payments = list(capped)
    else:
        # Largest remainder pro rata scale down to exactly the occurrence limit.
        floors = []
        remainders = []
        for i, c in enumerate(capped):
            scaled = c * per_occurrence_cents
            q, r = divmod(scaled, total)
            floors.append(q)
            remainders.append((-r, i))  # sort by remainder desc, index asc
        shortfall = per_occurrence_cents - sum(floors)
        payments = list(floors)
        for _, i in sorted(remainders)[:shortfall]:
            payments[i] += 1

    return BISettlement(tuple(losses_cents), per_person_cents, per_occurrence_cents,
                        tuple(capped), tuple(payments))


@dataclass
class RentalSettlement:
    daily_rate_cents: int
    days: int
    per_day_cap_cents: int
    aggregate_cap_cents: int
    per_day_paid_cents: int
    payment_cents: int


def settle_rental(daily_rate_cents: int, days: int, per_day_cap_cents: int,
                  aggregate_cap_cents: int) -> RentalSettlement:
    _check_amount("daily rate", daily_rate_cents)
    _check_amount("per day cap", per_day_cap_cents, allow_zero=False)
    _check_amount("aggregate cap", aggregate_cap_cents, allow_zero=False)
    if days < 0:
        raise ValueError("days must be >= 0")
    per_day = min(daily_rate_cents, per_day_cap_cents)
    payment = min(per_day * days, aggregate_cap_cents)
    return RentalSettlement(daily_rate_cents, days, per_day_cap_cents,
                            aggregate_cap_cents, per_day, payment)


@dataclass
class CoinsuranceSettlement:
    loss_cents: int
    property_value_cents: int
    coinsurance_pct_milli: int
    carried_limit_cents: int
    deductible_cents: int
    required_cents: int
    scaled_loss_cents: int  # after coinsurance penalty, before deductible
    payment_cents: int


def settle_coinsurance(loss_cents: int, property_value_cents: int,
                       coinsurance_pct_milli: int, carried_limit_cents: int,
                       deductible_cents: int) -> CoinsuranceSettlement:
    _check_amount("loss", loss_cents)
    _check_amount("property value", property_value_cents, allow_zero=False)
    _check_amount("carried limit", carried_limit_cents, allow_zero=False)
    _check_amount("deductible", deductible_cents)
    if not (0 < coinsurance_pct_milli <= 1000):
        raise ValueError("coinsurance percentage must be in (0, 1000] per mille")

    required = round_half_up_div(property_value_cents * coinsurance_pct_milli, 1000)
    if carried_limit_cents >= required or required == 0:
        scaled = loss_cents
    else:
        scaled = round_half_up_div(loss_cents * carried_limit_cents, required)
    after_deductible = max(0, scaled - deductible_cents)
    payment = min(after_deductible, carried_limit_cents)
    return CoinsuranceSettlement(loss_cents, property_value_cents, coinsurance_pct_milli,
                                 carried_limit_cents, deductible_cents, required,
                                 scaled, payment)
