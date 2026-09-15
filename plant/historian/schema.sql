-- CONV-001 historian — TimescaleDB schema.
--
-- Applied once at container init. Two design decisions carry the file.
--
-- 1. EVERY TIMESTAMP IS UTC. `timestamptz` throughout, the container runs
--    TZ=UTC, and rendering to Australia/Brisbane happens in the query or in
--    the dashboard and nowhere else (ADR-010). A historian that stores local
--    time acquires a one-hour hole and a one-hour overlap every year in any
--    DST zone, and the hole is indistinguishable from an outage.
--
-- 2. RAW DATA IS KEPT FOR 90 DAYS, AGGREGATES FOREVER. Predictive
--    maintenance at S13 needs long trends, not long samples. Keeping 1 Hz
--    raw for a year would be 31 million rows per tag to answer a question
--    that a 5-minute mean answers better.

CREATE EXTENSION IF NOT EXISTS timescaledb;

-- ---------------------------------------------------------------------------
-- Asset model — mirrors the ISA-95 hierarchy in the OPC UA address space
-- ---------------------------------------------------------------------------

CREATE TABLE asset (
    asset_id     text PRIMARY KEY,
    parent_id    text REFERENCES asset(asset_id),
    level        text NOT NULL CHECK (level IN
                     ('enterprise','site','area','cell','equipment')),
    display_name text NOT NULL
);

INSERT INTO asset VALUES
    ('ENT',            NULL,   'enterprise', 'Enterprise'),
    ('ENT.PIL',        'ENT',  'site',       'Pilbara Site'),
    ('ENT.PIL.PROC',   'ENT.PIL',  'area',   'Processing Area'),
    ('ENT.PIL.PROC.CONV', 'ENT.PIL.PROC', 'cell', 'Conveying Cell'),
    ('CONV001', 'ENT.PIL.PROC.CONV', 'equipment', 'Conveyor CONV-001');

-- ---------------------------------------------------------------------------
-- Tag dictionary — the engineering units live HERE, once
-- ---------------------------------------------------------------------------

CREATE TABLE tag (
    tag_id      text PRIMARY KEY,
    asset_id    text NOT NULL REFERENCES asset(asset_id),
    unit        text,
    description text NOT NULL,
    -- Alarm limits are attributes of the TAG, not of the SCADA screen.
    -- A limit that lives only in the HMI is a limit that disappears when
    -- somebody rebuilds the HMI, and nobody notices until the day it was
    -- needed.
    hi_hi       double precision,
    hi          double precision,
    lo          double precision,
    lo_lo       double precision
);

INSERT INTO tag (tag_id, asset_id, unit, description, hi_hi, hi, lo, lo_lo) VALUES
    ('CONV001.BearingTemp_C', 'CONV001', 'degC', 'Drive-end bearing temperature', 95, 85, NULL, NULL),
    ('CONV001.Vibration_mms', 'CONV001', 'mm/s', 'Drive-end vibration, RMS velocity', 7.1, 4.5, NULL, NULL),
    ('CONV001.Current_A',     'CONV001', 'A',    'Motor current',                    42, 38, NULL, NULL),
    ('CONV001.Speed_mps',     'CONV001', 'm/s',  'Belt speed',                     NULL, NULL, 2.0, 0.1),
    ('CONV001.Load_tph',      'CONV001', 't/h',  'Belt load',                      1100, 950, NULL, NULL),
    ('CONV001.Running',       'CONV001', NULL,   'Motor running',                  NULL, NULL, NULL, NULL),
    ('CONV001.SafetyTripped', 'CONV001', NULL,   'Safety function tripped',        NULL, NULL, NULL, NULL);

-- ---------------------------------------------------------------------------
-- The hypertable
-- ---------------------------------------------------------------------------

CREATE TABLE sample (
    ts       timestamptz      NOT NULL,   -- UTC. Always.
    tag_id   text             NOT NULL REFERENCES tag(tag_id),
    value    double precision,
    quality  smallint         NOT NULL DEFAULT 192
);

-- Quality follows the OPC UA convention: 192 = Good, 64 = Uncertain,
-- 0 = Bad. It is NOT NULL because a missing quality is silently read as
-- good, and "the value was bad and we plotted it anyway" is how a
-- maintenance model learns from a disconnected transmitter.

SELECT create_hypertable('sample', 'ts', chunk_time_interval => INTERVAL '1 day');
CREATE INDEX ON sample (tag_id, ts DESC);

ALTER TABLE sample SET (
    timescaledb.compress,
    timescaledb.compress_segmentby = 'tag_id',
    timescaledb.compress_orderby   = 'ts DESC'
);
SELECT add_compression_policy('sample', INTERVAL '7 days');
SELECT add_retention_policy('sample',   INTERVAL '90 days');

-- ---------------------------------------------------------------------------
-- Continuous aggregates — what actually survives
-- ---------------------------------------------------------------------------

CREATE MATERIALIZED VIEW sample_5m
WITH (timescaledb.continuous) AS
SELECT tag_id,
       time_bucket('5 minutes', ts) AS bucket,
       avg(value)   AS avg_value,
       min(value)   AS min_value,
       max(value)   AS max_value,
       count(*)     AS n,
       count(*) FILTER (WHERE quality <> 192) AS n_not_good
FROM sample
GROUP BY tag_id, bucket
WITH NO DATA;

-- n_not_good is carried through the aggregate on purpose. An average that
-- silently includes bad-quality samples is worse than no average, and the
-- count is the only thing downstream can use to tell the difference.

SELECT add_continuous_aggregate_policy('sample_5m',
    start_offset      => INTERVAL '1 day',
    end_offset        => INTERVAL '5 minutes',
    schedule_interval => INTERVAL '5 minutes');

CREATE MATERIALIZED VIEW sample_1h
WITH (timescaledb.continuous) AS
SELECT tag_id,
       time_bucket('1 hour', ts) AS bucket,
       avg(value) AS avg_value,
       min(value) AS min_value,
       max(value) AS max_value,
       count(*)   AS n,
       count(*) FILTER (WHERE quality <> 192) AS n_not_good
FROM sample
GROUP BY tag_id, bucket
WITH NO DATA;

SELECT add_continuous_aggregate_policy('sample_1h',
    start_offset      => INTERVAL '7 days',
    end_offset        => INTERVAL '1 hour',
    schedule_interval => INTERVAL '30 minutes');

-- ---------------------------------------------------------------------------
-- Alarm history — see plant/alarms/ for the state model
-- ---------------------------------------------------------------------------

CREATE TABLE alarm_event (
    event_id    bigserial PRIMARY KEY,
    ts          timestamptz NOT NULL DEFAULT now(),
    tag_id      text        NOT NULL REFERENCES tag(tag_id),
    condition   text        NOT NULL,   -- HI_HI, HI, LO, LO_LO, DISCREPANCY…
    from_state  text        NOT NULL,
    to_state    text        NOT NULL,
    priority    smallint    NOT NULL,
    actor       text,                   -- who acknowledged, shelved, suppressed
    note        text
);
CREATE INDEX ON alarm_event (ts DESC);
CREATE INDEX ON alarm_event (tag_id, ts DESC);

-- The alarm history is APPEND ONLY and separate from the sample table.
-- Two reasons, and the second is the one that matters:
--
--   A state change is an event, not a measurement, and putting events in a
--   hypertable with a 90-day retention policy would silently delete the
--   record of why the plant stopped last quarter.
--
--   And the `actor` column is the whole point of alarm history at S24. The
--   question after an incident is rarely "did the alarm fire" — the log
--   shows that. It is "who shelved it, and when", which nothing records
--   unless somebody designed a column for it.

-- ---------------------------------------------------------------------------
-- Convenience: read the plant in Brisbane time (ADR-010)
-- ---------------------------------------------------------------------------

CREATE VIEW sample_aest AS
SELECT ts AT TIME ZONE 'Australia/Brisbane' AS ts_aest,
       ts AS ts_utc,
       tag_id, value, quality
FROM sample;

COMMENT ON VIEW sample_aest IS
 'Presentation only. Stored values are UTC; this view renders them in AEST '
 '(UTC+10, no daylight saving). Never write through this view. ADR-010.';
