#!/bin/bash
# Runs once when the Postgres container is first created (docker-entrypoint-initdb.d).
# Three roles, none of them superusers:
#   setwise_owner  creates tables (migrations only)
#   setwise_app    used by the API: DML only, subject to row-level security
#   setwise_maint  used by the daily retention job: can only delete expired data
set -euo pipefail
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<SQL
CREATE ROLE setwise_owner LOGIN PASSWORD '${SETWISE_OWNER_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE ROLE setwise_app   LOGIN PASSWORD '${SETWISE_APP_PASSWORD}'   NOSUPERUSER NOCREATEDB NOCREATEROLE NOBYPASSRLS;
CREATE ROLE setwise_maint LOGIN PASSWORD '${SETWISE_MAINT_PASSWORD}' NOSUPERUSER NOCREATEDB NOCREATEROLE;
CREATE DATABASE setwise OWNER setwise_owner;
REVOKE ALL ON DATABASE setwise FROM PUBLIC;
GRANT CONNECT ON DATABASE setwise TO setwise_app, setwise_maint;
SQL
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname setwise <<SQL
REVOKE ALL ON SCHEMA public FROM PUBLIC;
GRANT ALL ON SCHEMA public TO setwise_owner;
SQL
