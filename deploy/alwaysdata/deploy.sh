#!/usr/bin/env bash
# Deploy GECP to alwaysdata from your machine (Linux, macOS or Git Bash on Windows).
#
#   deploy/alwaysdata/deploy.sh setup          first-time server layout and .env
#   deploy/alwaysdata/deploy.sh deploy         build, upload, release, restart, health check
#   deploy/alwaysdata/deploy.sh rollback [REL] switch back to the previous (or named) release
#   deploy/alwaysdata/deploy.sh backup         database + media backup on the server
#   deploy/alwaysdata/deploy.sh status         current release, history and disk usage
#   deploy/alwaysdata/deploy.sh restart        restart the Python site through the API
#   deploy/alwaysdata/deploy.sh logs           tail the site's uWSGI error log
#
# Settings: deploy/alwaysdata/deploy.env (copy deploy.env.example). Secrets stay out of it:
# export ALWAYSDATA_API_KEY in your shell to enable automatic restarts.
# Flags (environment): ALLOW_DIRTY=1 deploys uncommitted changes, SKIP_BUILD=1 reuses built assets,
# SKIP_HEALTHCHECK=1 skips the HTTPS check.
set -euo pipefail

HERE="$(cd "$(dirname "$0")" && pwd)"
PROJECT="$(cd "$HERE/../.." && pwd)"
CONFIG="${DEPLOY_CONFIG:-$HERE/deploy.env}"

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

[ -f "$CONFIG" ] || die "Missing $CONFIG. Copy deploy.env.example to deploy.env and fill it in."
# shellcheck disable=SC1090
. "$CONFIG"

: "${ALWAYSDATA_ACCOUNT:?Set ALWAYSDATA_ACCOUNT in deploy.env}"
[ "$ALWAYSDATA_ACCOUNT" != ACCOUNT ] || die "Replace the ACCOUNT placeholder in $CONFIG"
SSH_HOST="${SSH_HOST:-ssh-$ALWAYSDATA_ACCOUNT.alwaysdata.net}"
SSH_USER="${SSH_USER:-$ALWAYSDATA_ACCOUNT}"
SSH_PORT="${SSH_PORT:-22}"
# REMOTE_ROOT is a path on the server. A ~ in deploy.env was already expanded against the
# LOCAL home when the file was sourced, so strip that back off and let the server expand $HOME.
REMOTE_ROOT="${REMOTE_ROOT:-gecp}"
REMOTE_ROOT="${REMOTE_ROOT#"$HOME"/}"
REMOTE_ROOT="${REMOTE_ROOT#\~/}"
case "$REMOTE_ROOT" in
  /*) SCP_ROOT="$REMOTE_ROOT" ;;
  *) SCP_ROOT="$REMOTE_ROOT"; REMOTE_ROOT="\$HOME/$REMOTE_ROOT" ;;
esac
PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
KEEP_RELEASES="${KEEP_RELEASES:-5}"
BACKUP_KEEP="${BACKUP_KEEP:-14}"
TARGET="$SSH_USER@$SSH_HOST"
SSH_OPTS=(-p "$SSH_PORT" -o ServerAliveInterval=30)
REMOTE_ENV="APP_ROOT=$REMOTE_ROOT PYTHON_VERSION=$PYTHON_VERSION KEEP_RELEASES=$KEEP_RELEASES BACKUP_KEEP=$BACKUP_KEEP"

remote() { ssh "${SSH_OPTS[@]}" "$TARGET" "$@"; }
remote_script() { remote "$REMOTE_ENV bash $REMOTE_ROOT/current/deploy/alwaysdata/remote/$1 ${*:2}"; }

restart_site() {
  if [ -z "${SITE_ID:-}" ] || [ -z "${ALWAYSDATA_API_KEY:-}" ]; then
    warn "Restart the Python site now: alwaysdata panel > Web > Sites > restart."
    warn "(Set SITE_ID in deploy.env and export ALWAYSDATA_API_KEY to automate this.)"
    return 0
  fi
  log "Restarting site $SITE_ID through the alwaysdata API"
  local status
  status="$(curl -sS -o /dev/null -w '%{http_code}' -X POST --basic \
    --user "$ALWAYSDATA_API_KEY account=$ALWAYSDATA_ACCOUNT:" \
    "https://api.alwaysdata.com/v1/site/$SITE_ID/restart/")" || status=000
  case "$status" in
    2??) log "Site restart requested (HTTP $status)" ;;
    *) warn "API restart failed (HTTP $status). Restart the site in the panel." ;;
  esac
}

health_check() {
  [ "${SKIP_HEALTHCHECK:-0}" = 1 ] && return 0
  [ -n "${DOMAIN:-}" ] && [ "$DOMAIN" != YOUR_DOMAIN ] || { warn "DOMAIN not set; skipping health check"; return 0; }
  local url="https://$DOMAIN/healthz/" attempt
  log "Checking $url"
  for attempt in 1 2 3 4 5 6; do
    if curl -fsS --max-time 10 "$url" | grep -q '"ok"'; then
      log "Health check passed"
      return 0
    fi
    sleep 5
  done
  die "Health check failed for $url. Inspect: deploy.sh logs   Roll back: deploy.sh rollback"
}

build_bundle() {
  local bundle="$1"
  cd "$PROJECT"
  if [ "${ALLOW_DIRTY:-0}" != 1 ] && [ -n "$(git status --porcelain)" ]; then
    die "Uncommitted changes. Commit them, or rerun with ALLOW_DIRTY=1."
  fi
  if [ "${SKIP_BUILD:-0}" != 1 ]; then
    log "Building frontend assets"
    npm ci --no-audit --no-fund --loglevel=error
    npm run build --silent
  fi
  for built in static/css/app.css static/js/htmx.min.js static/js/alpine.min.js static/fonts; do
    [ -e "$built" ] || die "Missing built asset $built. Run npm run build."
  done
  log "Packing release bundle"
  # Tracked and new (non-ignored) files that exist, plus the git-ignored build output.
  {
    git ls-files -z --cached --others --exclude-standard | while IFS= read -r -d '' file; do
      [ -e "$file" ] && printf '%s\0' "$file"
    done
    printf '%s\0' static/css static/js/htmx.min.js static/js/alpine.min.js static/fonts
  } | tar --null -T - -czf "$bundle"
}

upload_and_extract() {
  local bundle="$1" release="$2"
  log "Uploading $(du -h "$bundle" | cut -f1) to $SSH_HOST"
  remote "mkdir -p $REMOTE_ROOT/incoming $REMOTE_ROOT/releases"
  scp -q -P "$SSH_PORT" "$bundle" "$TARGET:$SCP_ROOT/incoming/$release.tar.gz"
  remote "set -e; mkdir $REMOTE_ROOT/releases/$release; tar -xzf $REMOTE_ROOT/incoming/$release.tar.gz -C $REMOTE_ROOT/releases/$release; rm -f $REMOTE_ROOT/incoming/$release.tar.gz"
}

release_name() {
  local sha
  sha="$(git -C "$PROJECT" rev-parse --short HEAD 2>/dev/null || echo nogit)"
  [ -n "$(git -C "$PROJECT" status --porcelain 2>/dev/null)" ] && sha="$sha-dirty"
  printf '%s-%s' "$(date -u +%Y%m%d%H%M%S)" "$sha"
}

cmd="${1:-help}"
case "$cmd" in
  setup)
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    log "Uploading setup scripts"
    tar -czf "$tmp/setup.tar.gz" -C "$PROJECT" deploy/alwaysdata
    remote "mkdir -p $REMOTE_ROOT/incoming"
    scp -q -P "$SSH_PORT" "$tmp/setup.tar.gz" "$TARGET:$SCP_ROOT/incoming/setup.tar.gz"
    remote "set -e; d=\$(mktemp -d); tar -xzf $REMOTE_ROOT/incoming/setup.tar.gz -C \$d; $REMOTE_ENV bash \$d/deploy/alwaysdata/remote/setup.sh \$d; rm -rf \$d $REMOTE_ROOT/incoming/setup.tar.gz"
    ;;
  deploy)
    release="$(release_name)"
    tmp="$(mktemp -d)"; trap 'rm -rf "$tmp"' EXIT
    build_bundle "$tmp/release.tar.gz"
    upload_and_extract "$tmp/release.tar.gz" "$release"
    log "Activating release $release"
    remote "$REMOTE_ENV bash $REMOTE_ROOT/releases/$release/deploy/alwaysdata/remote/release.sh $REMOTE_ROOT/releases/$release"
    restart_site
    health_check
    log "Deployed $release"
    ;;
  rollback)
    remote_script rollback.sh "${2:-}"
    restart_site
    health_check
    ;;
  backup) remote_script backup.sh --with-media manual ;;
  restart) restart_site ;;
  status)
    remote "echo \"current: \$(readlink $REMOTE_ROOT/current 2>/dev/null || echo none)\"; echo; echo releases:; ls -1t $REMOTE_ROOT/releases 2>/dev/null; echo; echo recent deploys:; tail -n 10 $REMOTE_ROOT/deploy.log 2>/dev/null; echo; du -sh $REMOTE_ROOT/releases $REMOTE_ROOT/venvs $REMOTE_ROOT/shared/media $REMOTE_ROOT/shared/backups 2>/dev/null"
    ;;
  logs)
    [ -n "${SITE_ID:-}" ] || die "Set SITE_ID in deploy.env"
    remote "tail -n ${LINES:-100} ~/admin/logs/uwsgi/$SITE_ID.log"
    ;;
  help|-h|--help) sed -n '2,16p' "$0" | sed 's/^# \{0,1\}//' ;;
  *) die "Unknown command: $cmd (try: deploy.sh help)" ;;
esac
