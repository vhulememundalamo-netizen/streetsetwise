-- Applied after the tables exist, by the OWNER role (see app/migrate.py). Idempotent.
-- Goal: least privilege and defence in depth.
--   * setwise_app (the API) can only read/write rows whose user_id equals app.user_id,
--     which the API sets per request from the verified login token.
--   * It cannot change schema, cannot update or delete the audit log, and does not bypass RLS.

DO $$
DECLARE t text;
BEGIN
  FOREACH t IN ARRAY ARRAY['profiles','weight_logs','workouts','exercise_state','cardio_sessions',
                           'food_profiles','meal_plans','coach_messages','consents']
  LOOP
    EXECUTE format('ALTER TABLE %I ENABLE ROW LEVEL SECURITY', t);
    EXECUTE format('DROP POLICY IF EXISTS own_rows ON %I', t);
    EXECUTE format($p$CREATE POLICY own_rows ON %I
                      USING (user_id = current_setting('app.user_id', true))
                      WITH CHECK (user_id = current_setting('app.user_id', true))$p$, t);
  END LOOP;
END $$;

-- audit_log: anyone can append (login happens before we know who they are), but a user only reads their own events.
ALTER TABLE audit_log ENABLE ROW LEVEL SECURITY;
DROP POLICY IF EXISTS audit_insert ON audit_log;
DROP POLICY IF EXISTS audit_select ON audit_log;
CREATE POLICY audit_insert ON audit_log FOR INSERT WITH CHECK (true);
CREATE POLICY audit_select ON audit_log FOR SELECT USING (user_id = current_setting('app.user_id', true));

-- Grants
GRANT USAGE ON SCHEMA public TO setwise_app, setwise_maint;
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO setwise_app;
REVOKE UPDATE, DELETE ON audit_log FROM setwise_app;       -- append-only for the API
REVOKE ALL ON ALL TABLES IN SCHEMA public FROM setwise_maint;
GRANT SELECT, DELETE ON users, coach_messages, audit_log, auth_sessions TO setwise_maint;
