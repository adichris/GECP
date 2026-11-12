#!/usr/bin/env bash
# Point `current` back at an earlier release. Code only: database migrations are NOT
# reversed. Restore a pre-deploy dump from shared/backups if a migration must be undone.
# Usage: bash rollback.sh [RELEASE_NAME]   (default: the release before current)
set -euo pipefail
. "$(dirname "$0")/lib.sh"

current="$(current_release)"
[ -n "$current" ] || die "No current release to roll back from"

if [ -n "${1:-}" ]; then
  target="$RELEASES/$1"
else
  target="$(ls -1dt "$RELEASES"/*/ | sed 's#/$##' | grep -vxF "$current" | head -n 1 || true)"
fi
[ -n "$target" ] && [ -f "$target/manage.py" ] || die "No release to roll back to (available: $(ls -1 "$RELEASES" | tr '\n' ' '))"
[ -e "$target/.venv/bin/python" ] || die "$(basename "$target") has no virtualenv; redeploy it instead"

log "Rolling back $(basename "$current") -> $(basename "$target")"
switch_current "$target"
record rollback "$(basename "$target") (from $(basename "$current"))"
warn "Database schema was not changed. If the newer release applied migrations, check compatibility."
log "Restart the Python site to load $(basename "$target")"
