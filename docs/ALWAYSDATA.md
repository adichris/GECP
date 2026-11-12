# Deploy GECP to alwaysdata

Scripted deploys live in `deploy/alwaysdata/`. You run `deploy.sh` on your machine (Linux, macOS or Git Bash on Windows). It builds the frontend, uploads a release over SSH and activates it with the server-side scripts in `deploy/alwaysdata/remote/`.

Replace ACCOUNT, YOUR_DOMAIN and SITE_ID below. Use a custom domain for the programme subdomain network, and confirm DNS and certificate support before relying on nested subdomains of an alwaysdata.net address.

## Server layout

```
~/gecp/
  current -> releases/20261112093000-ab12cd3   the live release (atomic symlink)
  releases/<UTC timestamp>-<git sha>/           last KEEP_RELEASES releases
  venvs/<hash>/                                 one virtualenv per Python version + requirements.txt
  shared/.env                                   secrets and infrastructure (chmod 600, never in git)
  shared/local.py                               app choices, linked in as config/settings/local.py
  shared/media/                                 uploads, linked into every release
  shared/backups/                               pg_dump files and media archives (chmod 700)
  deploy.log                                    deploy and rollback history
```

A release whose `requirements.txt` is unchanged reuses the existing virtualenv, so most deploys take seconds.

## 1. Prepare hosting (once)

1. In the alwaysdata panel, create a PostgreSQL database and a user with access to it. Note the real names, which may carry an account prefix. The host is `postgresql-ACCOUNT.alwaysdata.net`.
2. Under Environment > Python, select Python 3.12.
3. Add your SSH public key under Remote access > SSH, and check that `ssh ACCOUNT@ssh-ACCOUNT.alwaysdata.net` works.

## 2. Configure your machine (once)

```sh
cp deploy/alwaysdata/deploy.env.example deploy/alwaysdata/deploy.env
```

Set `ALWAYSDATA_ACCOUNT`, `DOMAIN` and, once the site exists, `SITE_ID`. `deploy.env` is git-ignored and never uploaded.

For automatic restarts, create an API key under Profile > API keys and export it in your shell only. Never put it in a file:

```sh
export ALWAYSDATA_API_KEY=...
```

Without the key, deploy.sh prints a reminder to restart the site in the panel.

## 3. Create the server layout and .env

```sh
deploy/alwaysdata/deploy.sh setup
```

This creates `~/gecp` and two settings files. Re-running it is safe: existing files are never overwritten.
- `shared/.env`, from `deploy/alwaysdata/env.example`, with a freshly generated `SECRET_KEY`.
- `shared/local.py`, from `deploy/alwaysdata/local.py.example`.

Then edit `~/gecp/shared/.env` on the server (`ssh ...` then `nano ~/gecp/shared/.env`):

- `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `ADMIN_BASE_URL` for your domain.
- `DATABASE_URL`, with the username and password URL-encoded.
- The SMTP settings and `DEFAULT_FROM_EMAIL`.

Write plain `KEY=value` lines: no quotes and no `export`.

App behaviour lives in `~/gecp/shared/local.py`, which is plain Python, for example `SUBMISSION_NOTIFY_EMAILS = ['team@example.org']` or `SERVE_MEDIA = True`. Every release links it in as `config/settings/local.py`. It loads after `.env`, so it can override any setting. The production safety rules (DEBUG off, HTTPS, PostgreSQL, explicit hosts) are checked after it. Restart the site after editing either file. Releases refuse to activate while the file still contains placeholders. Never send secrets in chat or commit `.env`.

## 4. Deploy

```sh
deploy/alwaysdata/deploy.sh deploy
```

The script runs these steps in order:

1. Refuses to run with uncommitted changes (`ALLOW_DIRTY=1` overrides this).
2. Runs `npm ci && npm run build` (`SKIP_BUILD=1` reuses the existing build).
3. Packs the tracked files plus the built CSS, JS and fonts. Local `.env`, SQLite, `node_modules` and virtualenvs are never included.
4. Uploads the bundle and extracts it into `releases/<timestamp>-<sha>`.
5. On the server:
   - Links `shared/.env` and `shared/media` into the release.
   - Creates or reuses the virtualenv.
   - Runs `check --deploy` and `collectstatic`.
   - If migrations are pending, takes a `pg_dump` backup and then runs `migrate`.
   - Switches `current`.
   - Prunes old releases and unused virtualenvs.
6. Restarts the site through the API, or reminds you to restart it in the panel.
7. Checks `https://DOMAIN/healthz/` (`SKIP_HEALTHCHECK=1` skips this).

Any failure before the switch leaves the live release untouched.

### First deploy: initialise data deliberately

Only for a NEW EMPTY database, seed once after the first deploy:

```sh
cd ~/gecp/current
.venv/bin/python scripts/seed_all.py --settings config.settings.production --domain YOUR_DOMAIN --port 443
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py createsuperuser
```

Seeding reproduces the bundled content. It does not bring over local editorial changes, uploaded media, accounts or community activity. Never seed over a restored database. For restored content, update the existing Wagtail Sites to the final hostnames and port 443, keeping their root pages. Never re-seed with a different hostname as a substitute for a domain migration.

## 5. Configure the Python site (once)

Under Web > Sites > Add a site:

| Field | Value |
| --- | --- |
| Type | Python WSGI |
| Application path | /home/ACCOUNT/gecp/current/config/wsgi.py |
| Working directory | /home/ACCOUNT/gecp/current |
| Virtualenv | /home/ACCOUNT/gecp/current/.venv |
| Python | 3.12 (the same as `PYTHON_VERSION` in deploy.env) |
| Environment variable | DJANGO_SETTINGS_MODULE=config.settings.production |
| Addresses | YOUR_DOMAIN and every programme hostname below |

The paths go through the `current` symlink, so they never change between releases.

**Programme addresses.** Add gccs, pec, wwi, rengtech, spin, gsevs, tradestart, eraid, evm, dricd and tkrd, each followed by `.YOUR_DOMAIN`. All of them use ONE Python application. Register every address both in Web > Sites and in DNS. If you use www, redirect it to the canonical foundation hostname: the application rejects unregistered hosts.

**HTTPS.** Enable certificates and force HTTPS for every address.
- `TRUST_PROXY_SSL_HEADER=True` relies on alwaysdata's front proxy, which supplies X-Forwarded-Proto. Do not expose the app around that proxy.
- Keep the platform HTTP cache disabled for this dynamic app.
- HSTS includes subdomains, so confirm that every subdomain serves HTTPS before launch.

Copy the site ID from the site's URL in the panel into `SITE_ID` in deploy.env.

## 6. Media files (images and staff photos)

WhiteNoise serves `/static/`. Uploads live in `~/gecp/shared/media`, which every release links in as `media/`.

**Default: no setup needed.** With `SERVE_MEDIA = True` in `shared/local.py` (the default), the app serves public images itself.
- **What it serves:** `/media/images/` (Wagtail renditions), `/media/staff/photos/` and `/media/staff/portfolio/`.
- **What is refused (404):** everything else under `/media/`, including `media/documents/` and `media/original_images/`, and any non-image file.
- **Headers:** responses are cached for 30 days (`MEDIA_CACHE_SECONDS`) and sent with `nosniff`.

Wagtail documents always go through the permission-checked `/documents/` routes.

**Optional speed-up for busy sites:** let alwaysdata serve the images directly. Create a Static files site:
- **Addresses:** `YOUR_DOMAIN/media/images/` and `YOUR_DOMAIN/media/staff/`, plus the same two paths on every programme hostname.
- **Root directory:** `/home/ACCOUNT/gecp/shared/media/images` or `/home/ACCOUNT/gecp/shared/media/staff`, with one site per path.
- **Options:** enable Trim path and HTTPS.

Requests for those paths then never reach Python. You can keep `SERVE_MEDIA = True` as a fallback.

Never map `/media/` as a whole, `/media/documents/` or `/media/original_images/`. Never point a static site at a release directory or at `shared/.env`.

Verify a rendition and a staff photo URL in the browser after deploying.

## 7. Scheduled tasks

Under Advanced > Scheduled tasks, add two jobs that run as the account:

| Schedule | Command |
| --- | --- |
| Daily, 03:00 | `bash ~/gecp/current/deploy/alwaysdata/remote/maintenance.sh` (clearsessions and cleanup_community_limits) |
| Daily, 03:30 | `bash ~/gecp/current/deploy/alwaysdata/remote/backup.sh --with-media nightly` |

Backups keep the newest `BACKUP_KEEP` (default 14) of each kind. Copy them off the server regularly, and test a restore:

```sh
pg_restore --clean --no-owner --dbname="$DATABASE_URL" ~/gecp/shared/backups/db-....dump
```

## Day-to-day commands

| Command | What it does |
| --- | --- |
| `deploy.sh deploy` | Build, upload, migrate (with a backup first), switch, restart, health check |
| `deploy.sh rollback [RELEASE]` | Point `current` at the previous release (or a named one) and restart |
| `deploy.sh status` | Current release, releases on disk, recent history, disk usage |
| `deploy.sh backup` | Immediate database and media backup |
| `deploy.sh restart` | Restart the Python site through the API |
| `deploy.sh logs` | Tail `~/admin/logs/uwsgi/SITE_ID.log` (`LINES=300` for more) |

**Rollback is code only.** Migrations are not reversed. If the bad release changed the schema, check that the older code still works with it. Otherwise, restore the `db-...-pre-<release>.dump` that was taken right before that release migrated.

## Verify before announcing the launch

Check the following:
- Foundation and programme pages, CSS, JS, fonts and images.
- Global and per-site search.
- Admin login, forms, guest posting and moderation.
- Password recovery, using a real test mailbox, before you enable public registration.

Guest submissions stay pending until a moderator approves them.

Check that client IP handling sees distinct visitors. If REMOTE_ADDR is the real visitor, leave `TRUSTED_PROXY_IPS` empty. If it is the proxy peer, confirm the exact peer addresses with alwaysdata and set those. Never trust arbitrary forwarding headers, or many visitors will share one guest submission quota.

## Troubleshooting

- **Python errors:** run `deploy.sh logs`.
- **Host not configured (404):** the Wagtail Site hostname or port doesn't match the request.
- **Redirect loop:** the proxy HTTPS setting is missing.
- **Missing images:** check `SERVE_MEDIA` in `shared/local.py`. If you use static sites, check that they point at `shared/media/images` and `shared/media/staff`. Then check that the file exists under `~/gecp/shared/media`.
- **500 after a deploy:** read the log, then `deploy.sh rollback`. Never enable DEBUG publicly.
- **"still contains placeholders":** finish editing `~/gecp/shared/.env`.

## Official references

- [Python WSGI and virtual environments](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/)
- [PostgreSQL](https://help.alwaysdata.com/en/docs/web-hosting/databases/postgresql/)
- [SSH access](https://help.alwaysdata.com/en/docs/remote-access/ssh/)
- [API authentication](https://help.alwaysdata.com/en/docs/api/)
- [Site addresses and catch-all hosts](https://help.alwaysdata.com/en/docs/web-hosting/sites/add-a-site/)
- [Proxy headers](https://help.alwaysdata.com/en/docs/web-hosting/sites/http-stack/)
