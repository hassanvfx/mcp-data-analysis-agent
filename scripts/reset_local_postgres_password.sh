#!/bin/zsh
# Recover the local EDB PostgreSQL superuser password without deleting data.
set -euo pipefail

postgres_root="/Library/PostgreSQL/15"
data_dir="$postgres_root/data"
hba="$data_dir/pg_hba.conf"
psql="$postgres_root/bin/psql"
pg_ctl="$postgres_root/bin/pg_ctl"
[[ -x "$psql" && -x "$pg_ctl" ]] || { print -u2 "Expected EDB PostgreSQL 15 command-line tools were not found."; exit 2; }

cd /tmp
print "macOS will ask once for administrator authorization. PostgreSQL data is not deleted."
sudo -v
sudo test -f "$hba" || { print -u2 "Expected EDB PostgreSQL 15 data directory was not found."; exit 2; }

backup="$(mktemp /tmp/mcp-data-pg-hba.XXXXXX)"
temporary="$(mktemp /tmp/mcp-data-pg-hba-new.XXXXXX)"
owner="$(sudo stat -f '%u:%g' "$hba")"
mode="$(sudo stat -f '%Lp' "$hba")"
changed=false
restore_hba() {
  if [[ "$changed" == true ]]; then
    sudo cp "$backup" "$hba"
    sudo chown "$owner" "$hba"
    sudo chmod "$mode" "$hba"
    sudo -u postgres "$pg_ctl" reload -D "$data_dir" >/dev/null
  fi
  rm -f "$backup" "$temporary"
}
trap restore_hba EXIT

sudo cp "$hba" "$backup"
{ print -r -- "local all postgres trust"; cat "$backup"; } > "$temporary"
sudo cp "$temporary" "$hba"
sudo chown "$owner" "$hba"
sudo chmod "$mode" "$hba"
changed=true
sudo -u postgres "$pg_ctl" reload -D "$data_dir" >/dev/null

password="$(openssl rand -hex 32)"
print -r -- "ALTER ROLE postgres PASSWORD '$password';" | sudo -u postgres "$psql" -d postgres -v ON_ERROR_STOP=1 -q

# Restore normal authentication before retaining the newly generated credential.
restore_hba
changed=false

pgpass="$HOME/.pgpass"
entry="localhost:5432:*:postgres:${password}"
output="$(mktemp "${pgpass}.mcp-data.XXXXXX")"
{ [[ -f "$pgpass" ]] && grep -v '^localhost:5432:.*:postgres:' "$pgpass" || true
  print -r -- "$entry"
} > "$output"
chmod 600 "$output"
mv "$output" "$pgpass"

print "Local PostgreSQL superuser access was recovered and stored only in $pgpass."
print "Next run: ./scripts/setup_local_postgres_parity.sh"
