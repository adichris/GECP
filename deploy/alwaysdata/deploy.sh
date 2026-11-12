#!/usr/bin/env bash
# Deploy GECP in place. Run it on the server from the site directory:
#
#   cd ~/www/gecp && bash deploy/alwaysdata/deploy.sh [command]
#
# Commands:
#   deploy (default)            pull, install, build, check, back up + migrate, collectstatic, restart
#   setup                       first run: create .env and config/settings/local.py from the examples
#   backup [--with-media] [L]   database dump (and media archive) into BACKUP_DIR
#   maintenance                 clearsessions + cleanup_community_limits (for a scheduled task)
#   status                      deployed commit, recent deploys, pending migrations, disk usage
#   check                       Django deployment checks only
#
# Optional settings: deploy/alwaysdata/deploy.env in the site directory (see deploy.env.example)
# or environment variables. Flags: NO_PULL=1, SKIP_BUILD=1, ALLOW_DIRTY=1, SKIP_HEALTHCHECK=1.
set -euo pipefail

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

SITE_DIR="$(pwd -P)"
[ -f "$SITE_DIR/manage.py" ] && [ -d "$SITE_DIR/config/settings" ] \
  || die "Run this from the GECP site directory (the folder with manage.py). Current: $SITE_DIR"
cd "$SITE_DIR"

if [ -f deploy/alwaysdata/deploy.env ]; then
  # shellcheck disable=SC1091
  . deploy/alwaysdata/deploy.env
fi
export PYTHON_VERSION="${PYTHON_VERSION:-3.12}"  # alwaysdata picks the interpreter from this
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-config.settings.production}"
VENV="$SITE_DIR/.venv"
PY="$VENV/bin/python"
BACKUP_DIR="${BACKUP_DIR:-$HOME/backups/$(basename "$SITE_DIR")}"  # outside the web root
BACKUP_KEEP="${BACKUP_KEEP:-14}"
DEPLOY_LOG="$SITE_DIR/deploy.log"
ENV_FILE="$SITE_DIR/.env"
LOCAL_SETTINGS="$SITE_DIR/config/settings/local.py"
EXAMPLES="$SITE_DIR/deploy/alwaysdata"

manage() { "$PY" manage.py "$@"; }
record() { printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$DEPLOY_LOG"; }
commit() { git rev-parse --short HEAD 2>/dev/null || echo no-git; }
sha_of() { cat "$@" 2>/dev/null | sha256sum | cut -c1-16; }

# One deploy at a time.
lock() {
  command -v flock >/dev/null || return 0
  exec 9>"$SITE_DIR/.deploy.lock"
  flock -n 9 || die "Another deploy is running in $SITE_DIR"
}

# --------------------------------------------------------------------------------------------
setup_config() {
  local created=0
  umask 077
  if [ ! -f "$ENV_FILE" ]; then
    log "Creating .env from env.example with a fresh SECRET_KEY"
    local secret
    secret="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
    sed "s|^SECRET_KEY=.*|SECRET_KEY=$secret|" "$EXAMPLES/env.example" > "$ENV_FILE"
    created=1
  fi
  if [ ! -f "$LOCAL_SETTINGS" ]; then
    log "Creating config/settings/local.py from local.py.example"
    cp "$EXAMPLES/local.py.example" "$LOCAL_SETTINGS"
    created=1
  fi
  chmod 600 "$ENV_FILE" "$LOCAL_SETTINGS"
  if [ "$created" = 1 ]; then
    cat <<EOF

Edit the settings, then run the deploy again:
  $ENV_FILE                  secrets: domain/hosts, DATABASE_URL, SMTP
  $LOCAL_SETTINGS   server choices (may also hold DATABASES / EMAIL_*)
  bash deploy/alwaysdata/deploy.sh
EOF
    exit 0
  fi
  log ".env and local.py already exist; nothing to create"
}

require_config() {
  [ -f "$ENV_FILE" ] || [ -f "$LOCAL_SETTINGS" ] || { setup_config; }
  local unfinished
  unfinished="$( { grep -E '^[[:space:]]*[A-Za-z_]+=.*(REPLACE_WITH|YOUR_DOMAIN|DB_USER:URL_ENCODED|YOUR_SMTP)' "$ENV_FILE" 2>/dev/null || true; } \
    | cut -d= -f1 | tr -d ' ' | paste -sd, -)"
  if [ -n "$unfinished" ]; then
    die ".env still has example values for: $unfinished. Fill them in, or delete/comment out (#) the lines you set in local.py instead."
  fi
}

pull() {
  [ "${NO_PULL:-0}" = 1 ] && { log "Skipping git pull (NO_PULL=1)"; return 0; }
  git rev-parse --git-dir >/dev/null 2>&1 || { log "Not a git checkout; deploying the files as they are"; return 0; }
  git rev-parse --abbrev-ref '@{upstream}' >/dev/null 2>&1 || { log "No upstream branch; deploying the checkout as it is"; return 0; }
  if [ "${ALLOW_DIRTY:-0}" != 1 ] && ! { git diff --quiet && git diff --cached --quiet; }; then
    die "Tracked files were edited on the server. Commit/stash them, or rerun with ALLOW_DIRTY=1."
  fi
  log "Pulling $(git rev-parse --abbrev-ref '@{upstream}')"
  git pull --ff-only
}

python_env() {
  if [ ! -x "$PY" ]; then
    log "Creating virtualenv .venv (Python $PYTHON_VERSION)"
    python -m venv "$VENV"
    "$PY" -m pip install --quiet --upgrade pip
  fi
  local want have
  want="$(printf '%s\n' "$PYTHON_VERSION" | cat - requirements.txt | sha256sum | cut -c1-16)"
  have="$(cat "$VENV/.requirements.sha" 2>/dev/null || true)"
  if [ "$want" != "$have" ]; then
    log "Installing Python requirements"
    "$PY" -m pip install --quiet -r requirements.txt
    printf '%s\n' "$want" > "$VENV/.requirements.sha"
  else
    log "Python requirements unchanged"
  fi
}

frontend() {
  local built=(static/css/app.css static/js/htmx.min.js static/js/alpine.min.js static/fonts)
  if [ "${SKIP_BUILD:-0}" != 1 ] && command -v npm >/dev/null; then
    local want have
    want="$(sha_of package.json package-lock.json)"
    have="$(cat node_modules/.deploy.sha 2>/dev/null || true)"
    if [ ! -d node_modules ] || [ "$want" != "$have" ]; then
      log "Installing frontend packages"
      npm ci --no-audit --no-fund --loglevel=error
      printf '%s\n' "$want" > node_modules/.deploy.sha
    fi
    log "Building frontend assets"
    npm run build --silent
  elif [ "${SKIP_BUILD:-0}" != 1 ]; then
    warn "npm not found: using the built assets already in static/"
  fi
  for asset in "${built[@]}"; do
    [ -e "$asset" ] || die "Missing $asset. Install Node.js on the server or upload the built static/ files."
  done
}

# Export libpq variables for the configured database (works whether it is set in .env or local.py).
db_env() {
  eval "$("$PY" - <<'PY'
import shlex
import django
django.setup()
from django.conf import settings
db = settings.DATABASES['default']
if db['ENGINE'] != 'django.db.backends.postgresql':
    raise SystemExit('Backups need PostgreSQL; the configured engine is ' + db['ENGINE'])
for key, var in (('NAME', 'PGDATABASE'), ('USER', 'PGUSER'), ('PASSWORD', 'PGPASSWORD'),
                 ('HOST', 'PGHOST'), ('PORT', 'PGPORT')):
    value = str(db.get(key) or '')
    if value:
        print(f'export {var}={shlex.quote(value)}')
PY
)"
}

backup() {
  local with_media=0 label
  if [ "${1:-}" = "--with-media" ]; then with_media=1; shift; fi
  label="${1:-manual}"
  command -v pg_dump >/dev/null || die "pg_dump is not available in this shell"
  mkdir -p "$BACKUP_DIR"; chmod 700 "$BACKUP_DIR"
  local stamp dump
  stamp="$(date -u +%Y%m%dT%H%M%SZ)"
  dump="$BACKUP_DIR/db-$stamp-$label.dump"
  log "Backing up the database to $dump"
  (umask 077; db_env; pg_dump --format=custom --no-owner --file="$dump")
  [ -s "$dump" ] || die "Backup file is empty: $dump"
  if [ "$with_media" = 1 ] && [ -d media ]; then
    log "Archiving media to $BACKUP_DIR/media-$stamp-$label.tar.gz"
    (umask 077; tar -czf "$BACKUP_DIR/media-$stamp-$label.tar.gz" media)
  fi
  local pattern
  for pattern in 'db-*.dump' 'media-*.tar.gz'; do
    find "$BACKUP_DIR" -maxdepth 1 -name "$pattern" -printf '%T@ %p\n' 2>/dev/null \
      | sort -rn | tail -n +"$((BACKUP_KEEP + 1))" | cut -d' ' -f2- | xargs -r rm -f --
  done
  log "Backup complete ($(du -h "$dump" | cut -f1))"
}

restart() {
  if [ -n "${RESTART_COMMAND:-}" ]; then
    log "Restarting: $RESTART_COMMAND"
    bash -c "$RESTART_COMMAND" || warn "RESTART_COMMAND failed. Restart the site from the hosting panel."
  else
    warn "Restart the Python site now so it loads the new code (hosting panel > Sites > restart),"
    warn "or set RESTART_COMMAND in deploy/alwaysdata/deploy.env."
  fi
}

health_check() {
  if [ "${SKIP_HEALTHCHECK:-0}" = 1 ] || [ -z "${DOMAIN:-}" ]; then return 0; fi
  local url="https://$DOMAIN/healthz/" attempt
  log "Checking $url"
  for attempt in 1 2 3 4 5 6; do
    curl -fsS --max-time 10 "$url" 2>/dev/null | grep -q '"ok"' && { log "Health check passed"; return 0; }
    sleep 5
  done
  warn "Health check failed for $url after $attempt attempts. Check the site log."
  return 1
}

deploy() {
  lock
  require_config
  local before
  before="$(commit)"
  pull
  python_env
  frontend
  log "Running Django deployment checks"
  manage check --deploy
  if manage migrate --check >/dev/null 2>&1; then
    log "No pending migrations"
  else
    log "Pending migrations: backing up the database first"
    backup "pre-$(commit)"
    log "Applying migrations"
    manage migrate --noinput
  fi
  log "Collecting static files"
  manage collectstatic --noinput --verbosity 0
  record deploy "$(commit) (previous: $before)"
  restart
  health_check || true
  log "Deployed $(commit) from $SITE_DIR"
}

status() {
  echo "site:     $SITE_DIR"
  echo "commit:   $(commit)$(git log -1 --format=' - %s (%cr)' 2>/dev/null || true)"
  echo "settings: $DJANGO_SETTINGS_MODULE"
  echo
  echo "recent deploys:"; tail -n 10 "$DEPLOY_LOG" 2>/dev/null || echo "  none yet"
  echo
  if [ -x "$PY" ]; then
    if manage migrate --check >/dev/null 2>&1; then echo "migrations: up to date"; else echo "migrations: PENDING"; fi
  fi
  du -sh media "$BACKUP_DIR" 2>/dev/null || true
}

cmd="${1:-deploy}"
case "$cmd" in
  deploy) deploy ;;
  setup) setup_config ;;
  backup) shift; [ -x "$PY" ] || die "No .venv yet: run a deploy first"; backup "$@" ;;
  maintenance)
    log "Clearing expired sessions"; manage clearsessions
    log "Pruning expired community rate limits"; manage cleanup_community_limits ;;
  status) status ;;
  check) manage check --deploy ;;
  help|-h|--help) sed -n '2,15p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "Unknown command: $cmd (try: bash deploy/alwaysdata/deploy.sh help)" ;;
esac
