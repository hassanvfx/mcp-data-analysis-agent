#!/bin/zsh
# Create an isolated local PostgreSQL role/database for the optional live tests.
set -euo pipefail

database="${1:-mcp_data_parity}"
role="${2:-mcp_data_test}"
if [[ ! "$database" =~ '^[A-Za-z_][A-Za-z0-9_]{0,62}$' || ! "$role" =~ '^[A-Za-z_][A-Za-z0-9_]{0,62}$' ]]; then
  print -u2 "Database and role names must be simple PostgreSQL identifiers."
  exit 2
fi
for command in psql createdb openssl; do
  command -v "$command" >/dev/null || { print -u2 "Required command missing: $command"; exit 2; }
done

print "Using the local postgres superuser credential stored in ~/.pgpass."
role_exists="$(psql -h localhost -U postgres -d postgres -Atqc "SELECT 1 FROM pg_roles WHERE rolname = '$role'")"
database_exists="$(psql -h localhost -U postgres -d postgres -Atqc "SELECT 1 FROM pg_database WHERE datname = '$database'")"
if [[ -n "$role_exists" || -n "$database_exists" ]]; then
  print -u2 "Refusing to replace existing role or database. Choose different names or remove the disposable resources manually."
  exit 1
fi

password="$(openssl rand -hex 32)"
if ! print -r -- "CREATE ROLE \"$role\" LOGIN PASSWORD '$password';" | psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -q; then
  print -u2 "Could not create the local test role."
  exit 1
fi
if ! createdb -h localhost -U postgres -O "$role" "$database"; then
  psql -h localhost -U postgres -d postgres -v ON_ERROR_STOP=1 -q -c "DROP ROLE \"$role\""
  print -u2 "Could not create the local test database; the newly created role was removed."
  exit 1
fi

pgpass="$HOME/.pgpass"
temporary="$(mktemp "${pgpass}.mcp-data.XXXXXX")"
trap 'rm -f "$temporary"' EXIT
{ [[ -f "$pgpass" ]] && grep -v "^localhost:5432:${database}:${role}:" "$pgpass" || true
  print -r -- "localhost:5432:${database}:${role}:${password}"
} > "$temporary"
chmod 600 "$temporary"
mv "$temporary" "$pgpass"

print "Created disposable PostgreSQL parity database: $database"
print "Run: export MCP_DATA_TEST_POSTGRES_URL='postgresql://${role}@localhost:5432/${database}'"
print "Then: uv run pytest tests/test_postgres_contract.py tests/test_sqlite_postgres_parity.py -q"
