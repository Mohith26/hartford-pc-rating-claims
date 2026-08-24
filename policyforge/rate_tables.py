"""Illustrative rate tables.

These are invented but realistic looking numbers I made up for this project.
They are NOT filed rates from any insurer or state filing, and nothing here
should be used to price real insurance. The point of the project is the math
machinery around the tables, not the tables themselves.

Conventions:
  * Base rates are integer cents for a six month policy term.
  * Every factor is an integer scaled by 1000 (per mille), so 1275 means 1.275.
  * BI limit options are written per person / per occurrence in thousands,
    e.g. "50/100" means $50,000 per person and $100,000 per occurrence.
  * COLL and COMP options are deductibles in whole dollars.
  * RENT options are per day cap / aggregate cap in whole dollars.
"""

import copy

COVERAGES = ("BI", "PD", "COLL", "COMP", "RENT")

DEFAULT_TABLES = {
    "base_rate_cents": {
        "BI": 24000,
        "PD": 15000,
        "COLL": 30000,
        "COMP": 12000,
        "RENT": 3000,
    },
    "territory": {
        "T1": 950,
        "T2": 1100,
        "T3": 1275,
    },
    "driver_class": {
        "ADULT": 1000,
        "YOUTH": 1600,
        "SENIOR": 1050,
    },
    "tier": {
        "PREFERRED": 850,
        "STANDARD": 1000,
        "NONSTANDARD": 1450,
    },
    "coverage_options": {
        "BI": {
            "25/50": 1000,
            "50/100": 1180,
            "100/300": 1350,
            "250/500": 1520,
        },
        "PD": {
            "25": 1000,
            "50": 1120,
            "100": 1230,
        },
        "COLL": {
            "250": 1250,
            "500": 1000,
            "1000": 820,
        },
        "COMP": {
            "250": 1150,
            "500": 1000,
            "1000": 870,
        },
        "RENT": {
            "30/900": 1000,
            "50/1500": 1400,
        },
    },
}

# Dollar meanings of the option keys, used by the claims side so a quoted
# policy and a settled claim agree on what the limits actually are (cents).
BI_LIMITS_CENTS = {
    "25/50": (2500000, 5000000),
    "50/100": (5000000, 10000000),
    "100/300": (10000000, 30000000),
    "250/500": (25000000, 50000000),
}
PD_LIMITS_CENTS = {"25": 2500000, "50": 5000000, "100": 10000000}
DEDUCTIBLE_CENTS = {"250": 25000, "500": 50000, "1000": 100000}
RENT_CAPS_CENTS = {"30/900": (3000, 90000), "50/1500": (5000, 150000)}


def default_tables() -> dict:
    """A deep copy of the default tables, safe to mutate for scenarios."""
    return copy.deepcopy(DEFAULT_TABLES)


def revised_tables(overrides: dict) -> dict:
    """Build a revised table set from nested override paths.

    overrides maps tuple paths to new per mille values, for example
    {("territory", "T3"): 1350, ("tier", "NONSTANDARD"): 1550}.
    """
    tables = default_tables()
    for path, value in overrides.items():
        node = tables
        for key in path[:-1]:
            node = node[key]
        if path[-1] not in node:
            raise KeyError("unknown table path: {}".format(path))
        node[path[-1]] = value
    return tables
