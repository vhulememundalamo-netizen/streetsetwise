#!/bin/bash
# Starts a throwaway PostgreSQL on port 54329 for the test suite (needs the postgres OS user, e.g. in CI/containers).
set -euo pipefail
D=/tmp/pgtest
BIN=$(ls -d /usr/lib/postgresql/*/bin | tail -1)
if [ ! -d "$D" ]; then
  install -d -o postgres -g postgres "$D"
  su postgres -c "$BIN/initdb -D $D -A trust -U postgres >/dev/null"
fi
su postgres -c "$BIN/pg_ctl -D $D -o '-p 54329 -k /tmp' -l /tmp/pgtest.log -w start" || true
psql -h /tmp -p 54329 -U postgres -v ON_ERROR_STOP=1 postgres <<SQL
DROP DATABASE IF EXISTS setwise_test;
DROP ROLE IF EXISTS setwise_owner; DROP ROLE IF EXISTS setwise_app; DROP ROLE IF EXISTS setwise_maint;
CREATE ROLE setwise_owner LOGIN PASSWORD 'o' NOSUPERUSER;
CREATE ROLE setwise_app LOGIN PASSWORD 'a' NOSUPERUSER NOBYPASSRLS;
CREATE ROLE setwise_maint LOGIN PASSWORD 'm' NOSUPERUSER;
CREATE DATABASE setwise_test OWNER setwise_owner;
SQL
echo "export TEST_OWNER_URL=postgresql+psycopg://setwise_owner:o@127.0.0.1:54329/setwise_test"
echo "export TEST_APP_URL=postgresql+psycopg://setwise_app:a@127.0.0.1:54329/setwise_test"
echo "export TEST_MAINT_URL=postgresql+psycopg://setwise_maint:m@127.0.0.1:54329/setwise_test"
