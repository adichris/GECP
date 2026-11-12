#!/usr/bin/env bash
# Activate an extracted release: shared files, virtualenv, checks, static files,
# backup + migrations, then an atomic switch of `current`.
# Usage (normally via deploy.sh): bash release.sh RELEASE_DIR
set -euo pipefail
HERE="$(cd "$(dirname "$0")" && pwd)"
. "$HERE/lib.sh"

RELEASE="${1:?usage: release.sh RELEASE_DIR}"
RELEASE="$(cd "$RELEASE" && pwd)"
[ -f "$RELEASE/manage.py" ] || die "$RELEASE does not look like a GECP release"
require_env_file

log "Linking shared .env, local.py and media into $(basename "$RELEASE")"
ln -sfn "$ENV_FILE" "$RELEASE/.env"
if [ -f "$SHARED/local.py" ]; then
  ln -sfn "$SHARED/local.py" "$RELEASE/config/settings/local.py"
fi
rm -rf "$RELEASE/media"
ln -sfn "$SHARED/media" "$RELEASE/media"

# One virtualenv per (Python version, requirements) pair, reused across releases.
venv_key="$(printf '%s\n' "$PYTHON_VERSION" | cat - "$RELEASE/requirements.txt" | sha256sum | cut -c1-16)"
venv="$VENVS/$venv_key"
if [ ! -x "$venv/bin/python" ]; then
  log "Creating virtualenv $venv_key (Python $PYTHON_VERSION)"
  rm -rf "$venv.partial"
  python -m venv "$venv.partial"
  "$venv.partial/bin/python" -m pip install --quiet --upgrade pip
  "$venv.partial/bin/python" -m pip install --quiet -r "$RELEASE/requirements.txt"
  mv "$venv.partial" "$venv"
else
  log "Reusing virtualenv $venv_key"
fi
ln -sfn "$venv" "$RELEASE/.venv"

log "Running Django deployment checks"
manage "$RELEASE" check --deploy

log "Collecting static files"
manage "$RELEASE" collectstatic --noinput --verbosity 0

if manage "$RELEASE" migrate --check >/dev/null 2>&1; then
  log "No pending migrations"
else
  log "Pending migrations found: backing up the database first"
  BACKUP_KEEP="${BACKUP_KEEP:-14}" bash "$HERE/backup.sh" "pre-$(basename "$RELEASE")"
  log "Applying migrations"
  manage "$RELEASE" migrate --noinput
fi

previous="$(current_release)"
log "Switching current -> $(basename "$RELEASE")"
switch_current "$RELEASE"
record deploy "$(basename "$RELEASE") (previous: $([ -n "$previous" ] && basename "$previous" || echo none))"

# Prune old releases, never touching current or the one it replaced.
keep="${KEEP_RELEASES:-5}"
ls -1dt "$RELEASES"/*/ 2>/dev/null | sed 's#/$##' | tail -n +"$((keep + 1))" | while read -r old; do
  [ "$old" = "$RELEASE" ] || [ "$old" = "$previous" ] && continue
  log "Removing old release $(basename "$old")"
  rm -rf "$old"
done
# Virtualenvs no remaining release points at.
for env_dir in "$VENVS"/*/; do
  env_dir="${env_dir%/}"
  in_use=0
  for link in "$RELEASES"/*/.venv; do
    [ "$(readlink "$link" 2>/dev/null)" = "$env_dir" ] && in_use=1 && break
  done
  [ "$in_use" = 1 ] || { log "Removing unused virtualenv $(basename "$env_dir")"; rm -rf "$env_dir"; }
done

log "Release $(basename "$RELEASE") is live (restart the Python site to load it)"
