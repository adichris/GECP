# Verification — 30 September 2026

## Community release — 11 October 2026

- 65 Python tests pass, including registration, CSRF, cross-site/private comment rejection, locking, scoped moderation and audit records, escaping, author-only withdrawal, report deduplication, bookmarks, RSS privacy, recovery links, request limits and trusted proxy handling.
- Theme tests cover system changes, explicit choices, persistence, cross-tab updates, unavailable storage and legacy preferences.
- Ruff and migration consistency checks pass. Frontend compilation and static collection succeed.
- A fresh local database contains 12 sites, 25 blog posts and seven media-library entries. No fake member activity was seeded.
- Browser checks confirmed community filters, dark mode, article comments and the mobile registration layout. Local review uses port 8011.
- Docker/PostgreSQL execution, external SMTP delivery, DNS/TLS and backup recovery remain unverified. The supplied CI workflow has not run remotely.

## Completed locally

- 25 automated tests passed on Python 3.12 with SQLite, covering 12-site rendering, unknown-host rejection, repeatable seed data, scoped Wagtail and operations permissions, application deadlines, consent, CSRF, replay prevention, 11 programme-specific intake forms, global/site search, private-page exclusion and HTMX history restoration.
- Ruff checks passed.
- Django system checks passed; no missing migrations.
- Tailwind/daisyUI frontend build and static collection completed.
- Production `check --deploy` completed using PostgreSQL configuration without connecting to a live database. Its only warning is intentional: HSTS preload is disabled. Preload should be a deliberate domain-owner decision after every subdomain supports HTTPS.
- Browser review covered the foundation hero, six-pillar mega menu, interactive programme filter, global search results, per-site appearance controls, responsive layouts and mobile enquiry presentation.

## Deployment status

The local preview uses SQLite and Django’s development server. Docker is not installed on this machine, so the Docker image, Compose services and live PostgreSQL tests have not been executed locally. A CI workflow is provided to test PostgreSQL and build the image after the project is placed in a repository; that workflow has not run here.

Before public operation: configure the real domains and site ports, HTTPS and trusted proxy, PostgreSQL, durable media storage, backups and recovery checks. Create named administrator accounts. Replace the starter privacy notice with the organisation’s approved notice and establish a retention/follow-up process. Submissions are stored in the admin queue; automated email delivery, appointment scheduling, payments and complex placement workflows are not implemented.

## Content and media

Programme descriptions were adapted from the available GECP chat history. Seven media items are available: original identities, clearly marked archive graphics and one labelled conceptual illustration. Current service availability remains subject to GECP editorial confirmation. Demonstration events, news and resources are unpublished; no fictional partner is displayed. The confirmed postal address is P.O. Box AN 29512, Accra.

## Reproduce

Run `npm ci`, `npm run build`, `python manage.py migrate`, `python manage.py seed_gecp`, `pytest`, `ruff check .` and `python manage.py makemigrations --check --dry-run`. For production, follow the domain and deployment steps in README.md.

## Seed script verification — 5 October 2026

The unified `scripts/seed_all.py` passed a fresh SQLite database run and a repeat run with all seven asset files. Counts remained 169 pages (including unpublished starter pages), 12 sites, 10 image records (brand and library copies) and seven library entries. A manually edited About page was preserved. All 30 automated tests and Ruff checks passed. PostgreSQL/Docker execution remains unverified locally.

## Programme editorial expansion

33 tests pass, including all 11 expanded homepages, 22 blog detail pages, site-scoped topic filtering, exclusion of unpublished articles and preservation of edited content on repeat seeding. Ruff checks and migration consistency checks pass. The frontend build and search index update succeeded. An older Python server owned by another Windows process still serves port 8000; stopping it was denied by Windows. Restart it from this project folder to preview these changes.

## Independent blog seeder

38 tests pass, including full/repeat blog seeding, preservation of edited and unpublished posts, selected-site drafts, a read-only dry run, foundation article rendering, invalid site rejection and slug collision rollback. Ruff passes. The local execution created three GECP posts and preserved all 22 programme posts.

Guest release: verified random name/emoji selection in the browser, custom names, guest pending activity, session ownership, withdrawal, issue resolution, CSRF, validation, replay rejection and IP limits.
