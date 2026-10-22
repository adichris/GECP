# Deploy the approved GECP version to Alwaysdata

This guide deploys the Documents/Codex project that was previewed on port 8011. No remote deployment has been performed. Replace ACCOUNT and YOUR_DOMAIN below. Use a custom domain for the complete programme subdomain network; confirm DNS and certificate support before using nested subdomains of an alwaysdata.net address.

## 1. Prepare hosting

In Alwaysdata create a PostgreSQL database and database user, granting that user access to that database. Note the actual names (which may have an account prefix). Database host: postgresql-ACCOUNT.alwaysdata.net. Select Python 3.12 under Environment > Python and use that same version for the web site and virtual environment.

Upload the current source ZIP with SFTP and extract it into /home/ACCOUNT/www/gecp-platform. Do not upload your Windows virtual environment, node_modules, local .env or SQLite database as production configuration. The ZIP includes compiled CSS/JS and original seed assets.

SSH into the account, then run:

```sh
cd /home/ACCOUNT/www/gecp-platform
python -m venv .venv
.venv/bin/python -m pip install -r requirements.txt
cp deploy/alwaysdata/env.example .env
chmod 600 .env
```

Edit .env on the server with the actual domain, PostgreSQL credentials and SMTP settings. Generate SECRET_KEY locally on the server using `.venv/bin/python -c "import secrets; print(secrets.token_urlsafe(64))"`. URL-encode database username/password components when constructing DATABASE_URL. Do not send secrets in chat or commit .env.

Export settings for every shell session: manage.py otherwise defaults to development settings BEFORE reading .env.

```sh
export DJANGO_SETTINGS_MODULE=config.settings.production
.venv/bin/python manage.py check
.venv/bin/python manage.py migrate
```

## 2. Choose data initialization deliberately

For a NEW EMPTY production database, recreate the bundled content, blogs and assets:

```sh
.venv/bin/python scripts/seed_all.py --settings config.settings.production --domain YOUR_DOMAIN --port 443
.venv/bin/python manage.py createsuperuser
.venv/bin/python manage.py collectstatic --noinput
.venv/bin/python manage.py check --deploy
```

This reproduces seeded content, not subsequent local editorial changes, uploaded media, accounts or community activity. If you need those existing records, first arrange a separate data migration and copy media; do not seed over a restored database. Back up the local database/media and the remote database before migration. For restored content, update the existing Wagtail Sites to the final foundation/programme hostnames and port 443, preserving their root pages and Programme links. Never rerun seeding with a different hostname as a substitute for a domain migration.

## 3. Configure the Python site

Under Web > Sites > Add a site:

| Field | Value |
| --- | --- |
| Type | Python WSGI |
| Application path | /home/ACCOUNT/www/gecp-platform/config/wsgi.py |
| Working directory | /home/ACCOUNT/www/gecp-platform |
| Virtualenv | /home/ACCOUNT/www/gecp-platform/.venv |
| Python | 3.12, matching the virtual environment |
| Environment variable | DJANGO_SETTINGS_MODULE=config.settings.production |
| Addresses | YOUR_DOMAIN and every programme hostname below |

Addresses: gccs, pec, wwi, rengtech, spin, gsevs, tradestart, eraid, evm, dricd and tkrd, each followed by .YOUR_DOMAIN. All use ONE Python application. Configure DNS records using the targets shown by Alwaysdata. Register addresses in Web > Sites as well as DNS. If using www, configure a redirect to the canonical foundation hostname; the application deliberately rejects unregistered hosts.

Enable HTTPS certificates and force HTTPS for all addresses. TRUST_PROXY_SSL_HEADER=True is specific to Alwaysdata's documented front proxy, which supplies X-Forwarded-Proto. Do not expose the app directly around that proxy. Keep the platform HTTP cache disabled for this dynamic app to avoid caching sessions/forms. Django production settings enable HSTS including subdomains: confirm every relevant subdomain supports HTTPS before launch.

## 4. Serve images without exposing private documents

WhiteNoise serves collected /static/ files. It does NOT serve uploaded media.

Create a separate Alwaysdata Static files site with addresses YOUR_DOMAIN/media/images/ and the corresponding /media/images/ path on every programme hostname. Root directory: /home/ACCOUNT/www/gecp-platform/media/images. Enable Trim path and HTTPS. Verify an actual original and rendition URL in the browser.

Only map media/images, not the entire media directory. Wagtail documents must continue through Django's permission-checking /documents/ routes. Do not create a static /media/documents/ mapping. Never point a static site at the source directory or .env.

## 5. Verify before announcing the launch

Restart the Python site in the Alwaysdata panel after configuration changes. Check foundation and programme pages, CSS/JS, images, global/site search, admin login, forms, guest posting, moderation and password recovery. Guest submissions remain pending until moderators approve them. Verify a successful recovery email using a real test mailbox before enabling account registration publicly.

Check that client IP handling sees distinct visitors. If REMOTE_ADDR is the actual visitor, leave TRUSTED_PROXY_IPS empty. If it is the proxy peer, obtain/verify exact peer addresses with Alwaysdata and set those; never trust arbitrary client forwarding headers. Otherwise many visitors could share the same guest submission quota.

Set scheduled tasks to run `.venv/bin/python manage.py clearsessions` and `.venv/bin/python manage.py cleanup_community_limits` daily, from the project directory with DJANGO_SETTINGS_MODULE=config.settings.production. Back up PostgreSQL and the media directory, keep an independent copy and test a restore. Before updates, back up data; retain the previous source release and use a maintenance window for migrations. Do not assume reverting source reverses database changes.

Python errors: /home/ACCOUNT/admin/logs/uwsgi/SITE_ID.log. A host-not-configured 404 means Wagtail hostname/port and the request disagree. Repeated HTTPS redirects usually indicate the proxy HTTPS setting is missing. Missing images usually mean the media/images static route is missing. A 500 after installing dependencies requires reading the server log rather than enabling DEBUG publicly.

## Official references

- [Python WSGI and virtual environments](https://help.alwaysdata.com/en/docs/web-hosting/languages/python/configuration/)
- [PostgreSQL](https://help.alwaysdata.com/en/docs/web-hosting/databases/postgresql/)
- [Site addresses and catch-all hosts](https://help.alwaysdata.com/en/docs/web-hosting/sites/add-a-site/)
- [Proxy headers](https://help.alwaysdata.com/en/docs/web-hosting/sites/http-stack/)
- [Static path hosting and Trim path](https://help.alwaysdata.com/en/blog/2023-02-01-devops-react-we-can-be-heroes-just-for-one-app/)
