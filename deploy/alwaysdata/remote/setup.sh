#!/usr/bin/env bash
# First-time server preparation. Safe to re-run: never overwrites an existing .env.
# Usage (normally via `deploy.sh setup`): bash setup.sh /path/to/extracted/source
set -euo pipefail
. "$(dirname "$0")/lib.sh"

SOURCE="${1:?usage: setup.sh SOURCE_DIR}"

log "Creating $APP_ROOT layout"
mkdir -p "$RELEASES" "$SHARED/media" "$SHARED/backups" "$VENVS"
chmod 700 "$SHARED/backups"

if [ -f "$ENV_FILE" ]; then
  log "Keeping existing $ENV_FILE"
else
  log "Creating $ENV_FILE from env.example with a fresh SECRET_KEY"
  umask 077
  secret="$(python -c 'import secrets; print(secrets.token_urlsafe(64))')"
  sed "s|^SECRET_KEY=.*|SECRET_KEY=$secret|" "$SOURCE/deploy/alwaysdata/env.example" > "$ENV_FILE"
  chmod 600 "$ENV_FILE"
fi

if [ -f "$SHARED/local.py" ]; then
  log "Keeping existing $SHARED/local.py"
else
  log "Creating $SHARED/local.py from local.py.example"
  install -m 600 "$SOURCE/deploy/alwaysdata/local.py.example" "$SHARED/local.py"
fi

python_version="$(python --version 2>&1)"
log "Server Python for this shell: $python_version (PYTHON_VERSION=$PYTHON_VERSION)"

cat <<EOF

Next steps
1. Edit $ENV_FILE on the server: domain, DATABASE_URL and SMTP.
   Edit $SHARED/local.py for app choices: media serving and notification addresses.
2. Run the first deploy from your machine:   deploy/alwaysdata/deploy.sh deploy
3. For a NEW EMPTY database only, seed once on the server:
     cd $CURRENT && .venv/bin/python scripts/seed_all.py --settings config.settings.production --domain YOUR_DOMAIN --port 443
     cd $CURRENT && .venv/bin/python manage.py createsuperuser
4. In Web > Sites (Python WSGI):
     Application path   $CURRENT/config/wsgi.py
     Working directory  $CURRENT
     Virtualenv         $CURRENT/.venv
     Environment        DJANGO_SETTINGS_MODULE=config.settings.production
   Media: the app serves public images itself (SERVE_MEDIA in local.py). Optional speed-up: static sites
     for /media/images/ and /media/staff/ with roots $SHARED/media/images and $SHARED/media/staff.
EOF
