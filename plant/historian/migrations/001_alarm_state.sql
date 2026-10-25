-- 001 - alarm state persistence and an append-only alarm history (ADR-019).
--
-- schema.sql runs only on an EMPTY data volume (docker-entrypoint-initdb.d), so a
-- volume created before this change needs this file applied by hand. It is
-- idempotent: running it twice changes nothing.
--
--   Get-Content plant\historian\migrations\001_alarm_state.sql |
--     docker exec -i vigilimen-historian psql -U vigilimen -d vigilimen -v ON_ERROR_STOP=1
--
-- The same statements are in schema.sql for new volumes. FF-25 fails the build
-- if the two ever stop agreeing on the object names.

CREATE TABLE IF NOT EXISTS alarm_state (
    tag_id        text        NOT NULL REFERENCES tag(tag_id),
    condition     text        NOT NULL,
    state         text        NOT NULL,
    in_condition  boolean     NOT NULL,
    shelved_until timestamptz,
    pending_since timestamptz,
    updated_at    timestamptz NOT NULL,
    PRIMARY KEY (tag_id, condition)
);

CREATE OR REPLACE FUNCTION alarm_event_append_only() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'alarm_event is append-only: % refused', TG_OP;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS alarm_event_no_change ON alarm_event;
CREATE TRIGGER alarm_event_no_change
    BEFORE UPDATE OR DELETE ON alarm_event
    FOR EACH ROW EXECUTE FUNCTION alarm_event_append_only();

DROP TRIGGER IF EXISTS alarm_event_no_truncate ON alarm_event;
CREATE TRIGGER alarm_event_no_truncate
    BEFORE TRUNCATE ON alarm_event
    FOR EACH STATEMENT EXECUTE FUNCTION alarm_event_append_only();
