-- =============================================================================
--  Savings & Negotiation Tracker - schema
-- =============================================================================
--  A governed repository of sourcing savings initiatives. Every negotiation is
--  tracked from identification through realized savings, with an audit trail of
--  status/value changes for data governance.
-- =============================================================================

PRAGMA foreign_keys = ON;

-- -----------------------------------------------------------------------------
--  Reference: allowed status values (documents the workflow / drives validation)
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS status_ref (
    status      TEXT PRIMARY KEY,
    sort_order  INTEGER NOT NULL,
    is_terminal INTEGER NOT NULL DEFAULT 0   -- 1 = closed state (Realized/Cancelled)
);

INSERT OR IGNORE INTO status_ref (status, sort_order, is_terminal) VALUES
    ('Identified',     1, 0),
    ('In Negotiation', 2, 0),
    ('Agreed',         3, 0),
    ('Implemented',    4, 0),
    ('Realized',       5, 1),
    ('Cancelled',      6, 1);

-- -----------------------------------------------------------------------------
--  Core: one row per savings initiative / negotiation
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS initiatives (
    id                    INTEGER PRIMARY KEY AUTOINCREMENT,
    initiative_name       TEXT    NOT NULL,
    category              TEXT    NOT NULL,
    vendor                TEXT    NOT NULL,
    owner                 TEXT    NOT NULL,          -- analyst / buyer responsible
    savings_type          TEXT    NOT NULL,          -- Commodity, Freight, Payment Terms, ...
    currency              TEXT    NOT NULL DEFAULT 'USD',
    baseline_unit_cost    REAL    NOT NULL CHECK (baseline_unit_cost >= 0),
    negotiated_unit_cost  REAL    NOT NULL CHECK (negotiated_unit_cost >= 0),
    annual_volume         INTEGER NOT NULL CHECK (annual_volume >= 0),
    realized_savings      REAL    NOT NULL DEFAULT 0 CHECK (realized_savings >= 0),
    confidence            TEXT    NOT NULL DEFAULT 'Medium',  -- High / Medium / Low
    status                TEXT    NOT NULL DEFAULT 'Identified',
    start_date            TEXT    NOT NULL,           -- ISO date the work began
    target_close_date     TEXT,                       -- ISO date savings expected
    realized_date         TEXT,                       -- ISO date savings landed
    notes                 TEXT,
    created_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    updated_at            TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (status) REFERENCES status_ref (status)
);

CREATE INDEX IF NOT EXISTS ix_initiatives_status   ON initiatives (status);
CREATE INDEX IF NOT EXISTS ix_initiatives_category ON initiatives (category);
CREATE INDEX IF NOT EXISTS ix_initiatives_vendor   ON initiatives (vendor);

-- -----------------------------------------------------------------------------
--  Governance: append-only audit trail of changes
-- -----------------------------------------------------------------------------
CREATE TABLE IF NOT EXISTS audit_log (
    id            INTEGER PRIMARY KEY AUTOINCREMENT,
    initiative_id INTEGER NOT NULL,
    field_changed TEXT    NOT NULL,
    old_value     TEXT,
    new_value     TEXT,
    changed_by    TEXT    NOT NULL DEFAULT 'system',
    changed_at    TEXT    NOT NULL DEFAULT (datetime('now')),
    FOREIGN KEY (initiative_id) REFERENCES initiatives (id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS ix_audit_initiative ON audit_log (initiative_id);

-- -----------------------------------------------------------------------------
--  Convenience view: projected savings & realization rate per initiative
-- -----------------------------------------------------------------------------
DROP VIEW IF EXISTS v_initiative_metrics;
CREATE VIEW v_initiative_metrics AS
SELECT
    i.*,
    (i.baseline_unit_cost - i.negotiated_unit_cost) * i.annual_volume
        AS projected_savings,
    CASE
        WHEN (i.baseline_unit_cost - i.negotiated_unit_cost) * i.annual_volume > 0
        THEN i.realized_savings
             / ((i.baseline_unit_cost - i.negotiated_unit_cost) * i.annual_volume)
        ELSE NULL
    END AS realization_rate
FROM initiatives i;
