"""Shared domain constants and validation vocab for the Savings Tracker."""

STATUSES = [
    "Identified",
    "In Negotiation",
    "Agreed",
    "Implemented",
    "Realized",
    "Cancelled",
]

TERMINAL_STATUSES = {"Realized", "Cancelled"}

SAVINGS_TYPES = [
    "Commodity",
    "Freight",
    "Payment Terms",
    "Consolidation",
    "Resourcing",
    "Rebate",
    "Spec Change",
]

CONFIDENCE_LEVELS = ["High", "Medium", "Low"]

CURRENCIES = ["USD", "EUR", "CNY", "MXN"]

# Editable fields tracked in the audit log when they change.
AUDITED_FIELDS = [
    "initiative_name",
    "category",
    "vendor",
    "owner",
    "savings_type",
    "currency",
    "baseline_unit_cost",
    "negotiated_unit_cost",
    "annual_volume",
    "realized_savings",
    "confidence",
    "status",
    "start_date",
    "target_close_date",
    "realized_date",
    "notes",
]
