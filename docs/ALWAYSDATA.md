# Deploy GECP to alwaysdata

Deploys run **on the server, in the site directory**. Connect over SSH, `cd` into the folder that holds `manage.py`, and run:

```sh
bash deploy/alwaysdata/deploy.sh
```

The script works on the current directory. It needs no hosting account name, API key or upload step. `SITE` below means that directory, for example `/home/ACCOUNT/www/gecp`.

## What lives in the site directory

```
SITE/
  manage.py, apps/, config/ ...      the code (a git checkout, or files you uploaded)
  .env                               secrets and infrastructure (chmod 600, git-ignored)
  config/settings/local.py           server settings: database, email, app choices (chmod 600, git-ignored)
  .venv/                             virtualenv, rebuilt only when requirements.txt changes
  media/                             uploads
  staticfiles/                       collected static files
  deploy.log                         one line per deploy
~/backups/<site directory name>/     database dumps and media archives (outside the web root)
```

## 1. Prepare hosting (once)

1. Create a PostgreSQL database and a user with access to it. Note the real names, which may carry an account prefix.
2. Select Python 3.12 under Environment > Python.
3. Put the code in the site directory. Either `git clone` it there (deploys will then `git pull`), or upload the files.

The frontend build needs Node.js on the server. If `npm` isn't available, upload the built `static/css`, `static/js` and `static/fonts` folders along with the code, and the script uses them as they are.

## 2. First run: create the settings

```sh
cd SITE
bash deploy/alwaysdata/deploy.sh setup
```

This creates two files and never overwrites existing ones:

- **`.env`**, from `deploy/alwaysdata/env.example`, with a fresh `SECRET_KEY`. Set:
  - `ALLOWED_HOSTS`, `CSRF_TRUSTED_ORIGINS` and `ADMIN_BASE_URL` for your domain.
  - `DATABASE_URL` (URL-encode the username and password).
  - The SMTP settings and `DEFAULT_FROM_EMAIL`.

  Write plain `KEY=value` lines, with no quotes and no `export`.
- **`config/settings/local.py`**, from `deploy/alwaysdata/local.py.example`. This is plain Python that loads after `.env`, so it can override anything. Put the database (`DATABASES = {...}`) and email server (`EMAIL_*`) here instead of `.env` if you prefer. App choices go here too: `SERVE_MEDIA` and `SUBMISSION_NOTIFY_EMAILS`.

The production safety rules (DEBUG off, HTTPS, PostgreSQL, a strong `SECRET_KEY`, explicit hosts) are checked after both files load. Never commit either file or send its contents in chat.

## 3. Deploy

```sh
cd SITE
bash deploy/alwaysdata/deploy.sh
```

Steps, in order:

1. **Pull:** runs `git pull --ff-only` if the directory is a git checkout with an upstream branch. It refuses if tracked files were edited on the server (`ALLOW_DIRTY=1` overrides this; `NO_PULL=1` skips the pull).
2. **Python:** creates `.venv` if missing. Requirements are installed only when `requirements.txt` or `PYTHON_VERSION` changed.
3. **Frontend:** runs `npm ci` (only when the package files changed) and `npm run build`. `SKIP_BUILD=1` skips the build.
4. **Checks:** runs `manage.py check --deploy`.
5. **Migrations:** if any are pending, dumps the database to `~/backups/...` first, then migrates.
6. **Static files:** runs `collectstatic`.
7. **Record:** writes the commit to `deploy.log`.
8. **Restart:** runs `RESTART_COMMAND`, or reminds you to restart the site in the panel. **The new code is only live after a restart.**
9. **Health check:** checks `https://DOMAIN/healthz/` when `DOMAIN` is set.

Optional settings go in `deploy/alwaysdata/deploy.env` in the site directory (copy `deploy.env.example`), or in environment variables:

| Setting | Purpose |
| --- | --- |
| `PYTHON_VERSION` | Python version on the server (default 3.12) |
| `DOMAIN` | Turns on the HTTPS health check after each deploy |
| `RESTART_COMMAND` | Command that restarts the app; empty means a reminder |
| `BACKUP_DIR`, `BACKUP_KEEP` | Where backups go (default `~/backups/<site directory name>`) and how many of each kind to keep (default 14) |

Only one deploy can run at a time.

### First deploy: initialise data deliberately

Only for a NEW EMPTY database, seed once after the first deploy:

```sh
cd SITE
.venv/bin/python scripts/seed_all.py --settings config.settings.production --domain YOUR_DOMAIN --port 443
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py createsuperuser
DJANGO_SETTINGS_MODULE=config.settings.production .venv/bin/python manage.py seed_staff
```

Seeding reproduces the bundled content. It does not bring over local editorial changes, uploaded media, accounts or community activity. Never seed over a restored database. If the database was seeded or restored with other hostnames (for example `localhost:8000`), move every site at once with `python manage.py set_site_domain --domain YOUR_DOMAIN --port 443`. It only changes Wagtail Site hostnames and ports; pages and content stay.

### Rolling back

Deploys are in place, so a rollback means checking out the earlier commit and deploying it without pulling:

```sh
tail deploy.log                      # find the previous commit
git checkout <commit>
NO_PULL=1 bash deploy/alwaysdata/deploy.sh
```

Migrations are not reversed. If the bad deploy changed the schema, restore the `db-...-pre-<commit>.dump` it took first (see Backups below). Return to the branch with `git checkout main` before the next normal deploy.

## 4. Configure the Python site (once)

Under Web > Sites > Add a site:

| Field | Value |
| --- | --- |
| Type | Python WSGI |
| Application path | SITE/config/wsgi.py |
| Working directory | SITE |
| Virtualenv | SITE/.venv |
| Python | 3.12 (the same as `PYTHON_VERSION`) |
| Environment variable | DJANGO_SETTINGS_MODULE=config.settings.production |
| Addresses | YOUR_DOMAIN and every programme hostname below |

**Programme addresses.** Add gccs, pec, wwi, rengtech, spin, gsevs, tradestart, eraid, evm, dricd and tkrd, each followed by `.YOUR_DOMAIN`. All of them use ONE Python application. Register every address both in Web > Sites and in DNS. If you use www, redirect it to the canonical foundation hostname: the application rejects unregistered hosts.

**HTTPS.** Enable certificates and force HTTPS for every address.
- `TRUST_PROXY_SSL_HEADER=True` relies on alwaysdata's front proxy, which supplies X-Forwarded-Proto. Do not expose the app around that proxy.
- Keep the platform HTTP cache disabled for this dynamic app.
- HSTS includes subdomains, so confirm that every subdomain serves HTTPS before launch.

## 5. Media files (images and staff photos)

WhiteNoise serves `/static/`. Uploads live in `SITE/media`.

**Default: no setup needed.** With `SERVE_MEDIA = True` (the default), the app serves public images itself.
- **What it serves:** `/media/images/` (Wagtail renditions), `/media/staff/photos/` and `/media/staff/portfolio/`.
- **What is refused (404):** everything else under `/media/`, including `media/documents/` and `media/original_images/`, and any non-image file.
- **Headers:** responses are cached for 30 days (`MEDIA_CACHE_SECONDS`) and sent with `nosniff`.

Wagtail documents always go through the permission-checked `/documents/` routes.

**Optional speed-up:** let alwaysdata serve the images directly. Create Static files sites:
- **Addresses:** `YOUR_DOMAIN/media/images/` and `YOUR_DOMAIN/media/staff/`, plus the same two paths on every programme hostname.
- **Root directories:** `SITE/media/images` and `SITE/media/staff`, one site per path.
- **Options:** enable Trim path and HTTPS.

Never map `/media/` as a whole, `/media/documents/` or `/media/original_images/`. Never point a static site at the site directory itself: it holds `.env` and `local.py`.

## 6. Backups and scheduled tasks

```sh
bash deploy/alwaysdata/deploy.sh backup --with-media     # manual backup
```

Backups are custom-format `pg_dump` files plus an optional media archive, written to `BACKUP_DIR`. The database connection comes from Django's own settings, so it works whether the database is in `.env` or `local.py`. The newest `BACKUP_KEEP` of each kind are kept.

Under Advanced > Scheduled tasks, add:

| Schedule | Command |
| --- | --- |
| Daily, 03:00 | `cd SITE && bash deploy/alwaysdata/deploy.sh maintenance` |
| Daily, 03:30 | `cd SITE && bash deploy/alwaysdata/deploy.sh backup --with-media nightly` |

Copy backups off the server regularly, and test a restore:

```sh
pg_restore --clean --no-owner --dbname=DB_NAME --host=HOST --username=USER ~/backups/gecp/db-....dump
```

## Day-to-day commands (run in SITE)

| Command | What it does |
| --- | --- |
| `bash deploy/alwaysdata/deploy.sh` | Pull, install, build, check, back up and migrate, collectstatic, restart |
| `bash deploy/alwaysdata/deploy.sh status` | Deployed commit, recent deploys, pending migrations, disk usage |
| `bash deploy/alwaysdata/deploy.sh check` | Django deployment checks only |
| `bash deploy/alwaysdata/deploy.sh backup [--with-media] [label]` | Immediate backup |
| `bash deploy/alwaysdata/deploy.sh maintenance` | Clear expired sessions and community rate limits |
| `bash deploy/alwaysdata/deploy.sh setup` | Create `.env` and `local.py` if missing |

## Verify before announcing the launch

Check the following:
- Foundation and programme pages, CSS, JS, fonts and images, including staff photos.
- Global and per-site search.
- Admin login, forms, guest posting and moderation.
- Password recovery, using a real test mailbox, before you enable public registration.

Guest submissions stay pending until a moderator approves them.

Check that client IP handling sees distinct visitors. If REMOTE_ADDR is the real visitor, leave `TRUSTED_PROXY_IPS` empty. If it is the proxy peer, confirm the exact peer addresses with alwaysdata and set those. Never trust arbitrary forwarding headers, or many visitors will share one guest submission quota.

## Troubleshooting

- **Python errors:** read the site's log in `~/admin/logs/uwsgi/`.
- **"This hostname and port are not configured for a GECP site":** the Wagtail Sites don't match the domain. This usually happens when the database was seeded with the default `localhost:8000`. List them with `python manage.py shell -c "from wagtail.models import Site; print(list(Site.objects.values_list('hostname','port')))"`, then move them all with `python manage.py set_site_domain --domain YOUR_DOMAIN --port 443` (add `--dry-run` to preview).
- **Redirect loop:** `TRUST_PROXY_SSL_HEADER` is missing.
- **Missing images:** check `SERVE_MEDIA` in `local.py`, any static sites' roots, and that the file exists under `SITE/media`.
- **Old code still served:** restart the site.
- **500 after a deploy:** read the log, then roll back. Never enable DEBUG publicly.
- **".env still contains placeholders":** finish editing `.env`.

## Official references

- [Python WSGI and virtual environments](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/)
- [PostgreSQL](https://help.alwaysdata.com/en/docs/web-hosting/databases/postgresql/)
- [SSH access](https://help.alwaysdata.com/en/docs/remote-access/ssh/)
- [Site addresses and catch-all hosts](https://help.alwaysdata.com/en/docs/web-hosting/sites/add-a-site/)
- [Proxy headers](https://help.alwaysdata.com/en/docs/web-hosting/sites/http-stack/)
