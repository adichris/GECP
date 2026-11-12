#!/usr/bin/env bash
# Database backup (custom-format pg_dump), optionally with a media archive.
# Usage: bash backup.sh [--with-media] [label]
# Suitable for an alwaysdata scheduled task: bash ~/gecp/current/deploy/alwaysdata/remote/backup.sh --with-media nightly
set -euo pipefail
. "$(dirname "$0")/lib.sh"

with_media=0
if [ "${1:-}" = "--with-media" ]; then with_media=1; shift; fi
label="${1:-manual}"
keep="${BACKUP_KEEP:-14}"

database_url="$(env_get DATABASE_URL)"
[ -n "$database_url" ] || die "DATABASE_URL is not set in $ENV_FILE"
command -v pg_dump >/dev/null || die "pg_dump is not available in this shell"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
dump="$SHARED/backups/db-$stamp-$label.dump"
umask 077
log "Backing up database to $dump"
# libpq accepts postgres:// URIs directly, so credentials never appear in `ps` as separate flags.
pg_dump --format=custom --no-owner --file="$dump" "$database_url"
[ -s "$dump" ] || die "Backup file is empty: $dump"

if [ "$with_media" = 1 ] && [ -d "$SHARED/media" ]; then
  archive="$SHARED/backups/media-$stamp-$label.tar.gz"
  log "Archiving media to $archive"
  tar -czf "$archive" -C "$SHARED" media
fi

# Keep the newest $keep of each kind.
for pattern in 'db-*.dump' 'media-*.tar.gz'; do
  find "$SHARED/backups" -maxdepth 1 -name "$pattern" -printf '%T@ %p\n' 2>/dev/null \
    | sort -rn | tail -n +"$((keep + 1))" | cut -d' ' -f2- | xargs -r rm -f --
done
log "Backup complete ($(du -h "$dump" | cut -f1))"
