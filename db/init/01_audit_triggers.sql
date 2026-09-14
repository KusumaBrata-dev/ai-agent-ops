-- PostgreSQL init: dijalankan otomatis saat kontainer DB pertama dibuat
-- (docker-entrypoint-initdb.d). Versi PG dari trigger append-only SQLite.
-- Fase 4.2 PLAN.md; lihat docs/SCHEMA.md §audit_log.

-- ORM membuat skema via create_all (app startup); trigger ini dipasang ulang
-- idempotent oleh app saat init_db() mendeteksi PostgreSQL.
-- File ini tetap sebagai sumber kebenaran migration manual untuk DBA.

CREATE OR REPLACE FUNCTION forbid_audit_mutation() RETURNS trigger AS $$
BEGIN
    RAISE EXCEPTION 'audit_log is append-only';
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS audit_no_update ON audit_log;
CREATE TRIGGER audit_no_update BEFORE UPDATE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();

DROP TRIGGER IF EXISTS audit_no_delete ON audit_log;
CREATE TRIGGER audit_no_delete BEFORE DELETE ON audit_log
    FOR EACH ROW EXECUTE FUNCTION forbid_audit_mutation();
