# Shared helpers for the server-side scripts. Sourced, not executed.
# Layout under APP_ROOT (default ~/gecp):
#   releases/<timestamp>-<sha>/   one extracted source release per deploy
#   current -> releases/...       what the Python site serves
#   shared/.env                   production settings (chmod 600)
#   shared/media/                 uploads, linked into every release
#   shared/backups/               database dumps
#   venvs/<hash>/                 virtualenvs, reused while requirements are unchanged
#   deploy.log                    one line per deploy/rollback

APP_ROOT="${APP_ROOT:-$HOME/gecp}"
RELEASES="$APP_ROOT/releases"
SHARED="$APP_ROOT/shared"
VENVS="$APP_ROOT/venvs"
CURRENT="$APP_ROOT/current"
ENV_FILE="$SHARED/.env"
export PYTHON_VERSION="${PYTHON_VERSION:-3.12}"
export DJANGO_SETTINGS_MODULE=config.settings.production

log() { printf '\033[1;34m==>\033[0m %s\n' "$*"; }
warn() { printf '\033[1;33mwarning:\033[0m %s\n' "$*" >&2; }
die() { printf '\033[1;31merror:\033[0m %s\n' "$*" >&2; exit 1; }

# Read KEY from shared/.env without sourcing it (values may contain spaces or <>).
env_get() {
  [ -f "$ENV_FILE" ] || return 0
  local value
  value="$(grep -E "^[[:space:]]*$1=" "$ENV_FILE" | tail -n 1 | cut -d= -f2-)"
  value="${value%$'\r'}"
  value="${value#\"}"; value="${value%\"}"
  value="${value#\'}"; value="${value%\'}"
  printf '%s' "$value"
}

require_env_file() {
  [ -f "$ENV_FILE" ] || die "$ENV_FILE is missing. Run: deploy.sh setup"
  if grep -qE 'REPLACE_WITH|YOUR_DOMAIN|DB_USER:URL_ENCODED|YOUR_SMTP' "$ENV_FILE"; then
    die "$ENV_FILE still contains placeholders. Edit it on the server first."
  fi
}

# Atomically point `current` at a release directory.
switch_current() {
  local target="$1"
  ln -sfn "$target" "$APP_ROOT/.current.tmp"
  mv -Tf "$APP_ROOT/.current.tmp" "$CURRENT"
}

current_release() { [ -L "$CURRENT" ] && readlink "$CURRENT" || true; }

record() { printf '%s %s %s\n' "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" >> "$APP_ROOT/deploy.log"; }

manage() { (cd "$1" && "$1/.venv/bin/python" manage.py "${@:2}"); }
