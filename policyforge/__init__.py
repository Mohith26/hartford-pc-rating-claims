"""PolicyForge: a personal auto style rating and claims settlement engine.

All money is integer cents. All rating factors are integers scaled by 1000
(per mille), so 1.275 is stored as 1275. Rounding is half up and happens at
documented points only, which keeps every quote and settlement exactly
reproducible.
"""

__version__ = "1.0.0"
