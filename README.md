# GECP Digital Platform

## Latest community release

The current source includes moderated discussions and issues, blog comments and replies, account registration/recovery, bookmarks, RSS, contribution withdrawal, private data export and programme-scoped moderation. Every new contribution is reviewed before publication. The appearance selector offers Light, Dark and System default; light mode preserves suitable programme palettes.

See [Community operations](docs/COMMUNITY_OPERATIONS.md) for installation, moderator roles, SMTP, request limits and the local review port. See [Feature review and research](docs/FEATURES_AND_RESEARCH.md) for implemented functionality, sources and remaining operating requirements. Run `npm run test:theme` alongside `pytest` and `ruff check .`.

This release was developed in `outputs/gecp-platform-source/gecp-platform`. Its local review database uses port **8011** to avoid the older port-8000 server. Fresh installations can use the usual port 8000. Update previously extracted copies separately, preserving their database, media and environment files.

A runnable MVP of a modular Django/Wagtail monolith. One application and PostgreSQL database power a foundation website and independently branded programme websites. Python 3.12, Django 5.2 LTS, Wagtail 7.4 LTS, Tailwind 4, daisyUI 5, HTMX 2, Alpine.js 3, crispy forms and crispy-tailwind.

## Start with Docker

Install Docker Engine/Desktop with Compose. From this directory:

```sh
cp .env.example .env
docker compose build
docker compose up -d db
docker compose run --rm web python manage.py migrate
docker compose run --rm web python manage.py seed_gecp
docker compose run --rm web python manage.py createsuperuser
docker compose up -d web
```

PowerShell: use `Copy-Item .env.example .env` in place of `cp` if preferred. The supplied development database password is local-only. Never use it for deployment.

Open:

- Foundation: http://localhost:8000/
- Programmes: http://gccs.localhost:8000/, http://pec.localhost:8000/, http://wwi.localhost:8000/
- Also: `rengtech`, `spin`, `gsevs`, `tradestart`, `eraid`, `evm`, `dricd`, `tkrd` under `.localhost:8000`.
- Wagtail CMS: http://localhost:8000/admin/
- Programme hierarchy, partners and submissions: http://localhost:8000/operations/
- Readiness: http://localhost:8000/healthz/

Modern browsers resolve `*.localhost` to loopback. If your environment does not, add explicit programme hostnames pointing to `127.0.0.1` in your hosts file. Use the configured hostname and port: the application deliberately returns 404 for unregistered combinations.

The seed command is repeatable and preserves existing editorial changes. It creates source-based programme content, media, enquiry opportunities and editor groups, never user accounts or passwords. Earlier demonstration events and stories are retained as unpublished drafts. Archive graphics are clearly labelled. Replace the sample privacy notice before collecting real submissions.

## Run without Docker

Python 3.12 and Node.js 22+ are required. SQLite is supported only for a quick local preview and fast tests; PostgreSQL is required by production settings.

```sh
python -m venv .venv
# Linux/macOS: source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
pip install -r requirements-dev.txt
npm ci
npm run build
python manage.py migrate
python manage.py seed_gecp
python manage.py createsuperuser
python manage.py runserver
```

For this SQLite route, leave `.env` absent or remove `DATABASE_URL` from it. The Docker `.env.example` points at the Docker-only hostname `db`. For local PostgreSQL, set `DATABASE_URL=postgres://USER:PASSWORD@localhost:5432/gecp`.

`npm run build` compiles CSS and copies locally served HTMX/Alpine assets. There are no browser CDN dependencies. Rebuild after template or frontend changes. `npm run css:watch` watches CSS during development.

## Architecture

```text
config/          settings, URLs, WSGI
apps/core/       site routing, branding, navigation, pages, search
apps/programmes/ foundation and programme hierarchy, access membership, seed
apps/news/       NewsPage
apps/events/     EventPage with dates, venue and registration link
apps/opportunities/ OpportunityPage with deadline and application entry point
apps/resources/  ResourcePage with Wagtail document or external URL
apps/partners/   partners shared across selected sites
apps/engagement/ validated contact/application submissions and review admin
templates/       shared responsive layouts and HTMX partials
frontend/        Tailwind/daisyUI source and asset build
deploy/          reverse-proxy example
tests/           routing, isolation, permissions, validation and submission tests
```

The organisational hierarchy is relational:

```text
Foundation (one Wagtail Site)
  └─ Programme (one Wagtail Site)
      └─ Initiative
          └─ Project
              └─ Activity
```

The Wagtail page tree uses sibling homepages below the global root. Each homepage is a separate site's root. This is intentional: a programme's content cannot accidentally enter the foundation's descendant-based search. A foundation homepage links to programme sites through `Programme.site`. Initiative/project/activity records appear on programme homepages and are maintained in the operations admin; they are not duplicate Wagtail page records.

Each site owns its pages and branding. Shared models/templates provide common functionality, while title, tagline, logo, brand colour, default daisyUI theme, navigation, footer and contact information differ by site. Visitors can override themes, stored per site in local storage. Upload approved logos through **Settings → Site branding**; initials are used before logos are provided. Shared partners can be associated with several sites.

Content is edited in Wagtail, with its publishing/revision workflow. Add news, events, opportunities, resources and standard pages below the desired site's homepage. Contact forms and application forms work with and without JavaScript. HTMX enhances filtering, searching and form submission; Alpine filters the programme directory. Native disclosure menus work without JavaScript. Scroll reveals respect reduced-motion preferences.

Search uses Wagtail's database search backend. Visitors can choose the current site or the registered foundation network, with an optional programme filter. Both scopes exclude drafts and restricted pages. PostgreSQL gives the production search implementation. Rebuild the index with `python manage.py update_index` after bulk imports or backend changes. SEO fields, canonical URLs and a per-site `/sitemap.xml` are included.

## Editors and permissions

1. Create an editor through Wagtail's Users screen; enable staff status for operations-admin access.
2. Add the user to the relevant group, such as **GCCS editors**.
3. A platform administrator also creates a **Programme membership** for GCCS in the operations admin.

The group provides Wagtail page permissions on that site's subtree and image/document permissions on its media collection. Programme membership separately scopes operations-admin querysets and parent choices. Both normal model permissions and membership are required. This avoids mistaking Django's default model permissions for tenant isolation.

Programme editors can edit and publish their pages, maintain their hierarchy, and review submissions for their programme. They cannot modify other programme records by changing a URL or a parent field. Foundation submissions, programme/site creation, branding, navigation and shared partners are administered centrally by superusers in this MVP. Non-superusers should not receive global SiteBranding permission: Wagtail settings permissions are global rather than automatically scoped to programme membership.

This is shared organisational infrastructure, not a security boundary between unrelated customer organisations. Images and publicly published documents may be linked across sites. Use Wagtail collection restrictions for private documents. Page restriction rules and document restriction rules are separate. Database administrators and superusers can access all sites.

## Forms and personal data

Submissions are stored in the database with site, optional opportunity, consent, status, timestamp and a unique receipt. The visitor receives an on-screen confirmation; email delivery is not implemented. Forms require CSRF, validate opportunity scope/deadline, include a honeypot, throttle the session, and use a unique database-backed submission reference to prevent duplicate retries. The operations admin keeps submitted details read-only and allows status updates.

For a public deployment, configure the supplied edge rate limit, approve a real privacy notice, define a retention policy and establish staff review procedures. Session throttling alone does not stop a bot that discards cookies. No CV uploads, payments, scholarship decisions, counselling booking calendar or mailing workflow are implied by this MVP.

## Test and validate

```sh
ruff check .
python manage.py check
python manage.py makemigrations --check --dry-run
pytest
python manage.py collectstatic --noinput
```

Tests use an isolated SQLite database by default. For the PostgreSQL test path, set `DJANGO_SETTINGS_MODULE=config.settings.ci` and `DATABASE_URL` to a PostgreSQL database whose user can create a test database, then run `pytest`. CI runs tests with PostgreSQL 16, builds assets and builds the Docker image. See `VERIFICATION.md` for what was actually run in the build environment.

## Production deployment

1. Provision PostgreSQL, persistent media storage, DNS and HTTPS for the apex domain and programme subdomains. This repository does not provision a cloud account or certificates.
2. Set `.env`: a random `SECRET_KEY` of at least 50 characters, strong database credentials, explicit `ALLOWED_HOSTS` (for example `gecpfoundation.org,.gecpfoundation.org`), matching HTTPS `CSRF_TRUSTED_ORIGINS`, and `ADMIN_BASE_URL=https://gecpfoundation.org`.
3. Build and run migrations as an explicit release step, not in every web worker:

   ```sh
   docker compose -f compose.yaml -f compose.production.yaml build
   docker compose -f compose.yaml -f compose.production.yaml up -d db
   docker compose -f compose.yaml -f compose.production.yaml run --rm web python manage.py migrate
   docker compose -f compose.yaml -f compose.production.yaml run --rm web python manage.py check --deploy
   ```

4. For a fresh database only, seed with `python manage.py seed_gecp --domain gecpfoundation.org --port 443` inside the production web container. For an existing seeded database, edit the Site hostnames and ports in Wagtail instead; reseeding a new domain is rejected to avoid orphaning programme relationships.
5. Create the superuser interactively and replace demonstration content. Enable the production web service with `docker compose -f compose.yaml -f compose.production.yaml up -d web`.
6. Install a trusted HTTPS reverse proxy on the host using `deploy/nginx.conf.example` as a starting point. The application is bound to loopback only. The proxy must overwrite `X-Forwarded-Proto`; production Compose enables trust for that header. Do not expose this backend directly to untrusted clients.
7. For the example proxy's media alias, replace the named `media_data` volume with a bind mount at `/srv/gecp/media:/app/media` and make it writable by the container's `gecp` UID (inspect the image with `id gecp`). The proxy needs read access. Keep `/media/documents/` blocked so original documents are served through Wagtail's access checks. Static assets are served by WhiteNoise. Object storage is a future storage-backend option, not preconfigured here.
8. Verify the apex site, each subdomain, admin login, a real test submission, HTTPS redirects, document access and backups before opening the service publicly.

Production settings reject SQLite and weak development secrets and enable secure cookies, HTTPS redirection, HSTS and content-type protection. HSTS includes subdomains, so all configured subdomains must support HTTPS. `healthz` checks the database and is exempt from SSL redirection for local container health checks.

Schedule PostgreSQL backups and persistent-media backups, test restoration, monitor 5xx responses and readiness, and periodically prune sessions with `clearsessions`. Review submissions against your retention schedule. An example logical backup is `docker compose exec -T db pg_dump -U gecp -Fc gecp > gecp.dump` (use a binary-safe shell/redirection method; Windows PowerShell 5 redirection is not suitable for binary dumps). Do not treat a named Docker volume as a backup.

## Scope and next increments

Delivered: the multisite foundation, data hierarchy, content modules, responsive themes, contact/application intake, search, seed sites, scoped permissions, tests, build configuration and deployment guide.

Future increments should follow real programme workflows: booking and calendars, application review stages and notifications, portal accounts, document collection, analytics and per-site editor access to branding. There are no separate microservices or independently deployed programme projects.

Compatibility reference: [Wagtail's supported Django/Python versions](https://docs.wagtail.org/en/stable-7.4.x/releases/upgrading.html). Asset build reference: [daisyUI's Tailwind installation](https://daisyui.com/docs/install/).

## Enhanced public experience

The foundation page includes programme pathways, an editorial illustration, stories and a media collection. A six-pillar mega menu, mobile menu, complete contact footer and per-site colour themes are shared across all sites. Original GECP, GSEVS and WWI logos were recovered from the supplied chat history; other sites use text identities. The media library distinguishes identity, illustration and archived programme graphics.

`seed_gecp` also runs `enrich_gecp`. The latter can be rerun to add missing editorial pages and assets. It preserves edited pages, retires only identifiable demonstration content and fills empty contact fields. The confirmed address is P.O. Box AN 29512, Accra.

### Programme enquiry forms

Every site has contact, partnership and volunteering forms. Each programme also has a dedicated intake at `/participate/<kind>/`:

| Site | Kind | Purpose |
| --- | --- | --- |
| GCCS | learning | Learning interests and availability |
| PEC | guidance | Education and career guidance |
| WWI | work | Work experience and academic availability |
| RENGTECH | training | Technical training interests |
| SPIN | talent | Skills and collaborative projects |
| GSEVS | volunteer | Expertise and service preferences |
| TRADESTART | enterprise | Trade and enterprise support |
| ERAid | resources | Educational resource needs or offers |
| EVM | media | Education and research stories |
| DRICD | research | Research and documentation enquiries |
| TKRD | knowledge | Knowledge preservation enquiries |

Foundation forms include learning, volunteering, partnerships and media. Validated details are stored with the site and form kind in the operations admin. Submissions use CSRF protection, consent, honeypot checks, a session throttle and replay protection. They do not send email or promise bookings, placements or grants. Configure operational follow-up before launch.

See `docs/VERIFICATION.md` for the tested scope and deployment limitations.

## Seed everything with one script

After installing the Python dependencies and configuring the database, run from the project directory:

```sh
python scripts/seed_all.py --report seed-report.json
```

The script verifies SHA-256 checksums for all seven bundled assets, applies migrations, seeds the foundation and all 11 programme sites, imports branding and the media library, creates initiatives/projects/activities and editor groups, enriches the public content, and rebuilds search. It prints a site/media inventory and optionally saves it as JSON. Existing page content and logos are retained. It does not create accounts, passwords or fictional form submissions. Programme enquiry forms are configured in code and become available on the seeded sites.

```sh
# Verify the asset bundle without connecting to a database:
python scripts/seed_all.py --check-assets
# Seed data without importing media:
python scripts/seed_all.py --skip-assets
# Require migrations to be applied already:
python scripts/seed_all.py --no-migrate
# Fresh production database (configure production environment first):
python scripts/seed_all.py --settings config.settings.production --domain gecpfoundation.org --port 443
# Docker, after starting the database service:
docker compose run --rm web python scripts/seed_all.py
```

The script can be invoked by absolute path from another directory. Domain changes on an existing installation must be made in Wagtail Site settings; the script refuses to create a competing foundation hostname. Database seeding is transactional, but migrations and media storage are separate operations: an interrupted import can leave unused files, so rerun the script to complete it. Back up the database and media before seeding an existing production installation.

Data sources: `apps/programmes/catalogue.py`, the `seed_gecp`/`enrich_gecp` management commands, and `seed_assets/manifest.json` plus `illustration-provenance.json`. Only bundled, retrieved assets are imported; missing official logos retain text identities. Editorial notes and archive labels remain intact.

## Programme homepages and journals

Each programme homepage now has editable Wagtail sections for audiences, participation steps and FAQs. Edit these under the homepage’s **Programme sections** field. The source editorial data is in `apps/programmes/editorial.py`.

Each site has `/blog/`, topic filtering, article pages with reading time, and related programme articles. NewsPage now distinguishes Blog post from Programme insight. Add a News page under the relevant homepage and select **Blog post** to publish to its journal. The foundation journal brings together public blog posts from its registered programme network.

Apply the expansion to an existing database:

```sh
python manage.py migrate
python manage.py seed_programme_editorial
python manage.py update_index
npm run build
```

Restart the running server after applying model changes. The full `scripts/seed_all.py` also includes this expansion. Existing homepage sections and articles are preserved by the seed command. The 22 starter articles are explanatory programme guides, not reports of completed projects, verified placements or active funding calls.

## Seed blogs independently

After `python manage.py migrate` and the initial site seed, run:

```sh
# GECP plus all 11 programmes: 25 starter articles
python scripts/seed_blogs.py
# Foundation only: 3 articles
python scripts/seed_blogs.py --sites gecp
# Selected programmes: 2 articles per programme
python scripts/seed_blogs.py --sites wwi gccs pec
# Preview the creation/preservation plan without writing anything
python scripts/seed_blogs.py --sites all --dry-run
# Create missing posts as drafts for editorial review
python scripts/seed_blogs.py --sites gsevs rengtech --draft
# Equivalent Django command, including inside Docker
python manage.py seed_blogs --sites all
docker compose run --rm web python manage.py seed_blogs --sites all
```

Supported codes: `gecp gccs pec wwi rengtech spin gsevs tradestart eraid evm dricd tkrd`. Omit `--sites` to select all. Use `--settings config.settings.production` or `DJANGO_SETTINGS_MODULE` for the configured production database. This blog-only script does not migrate, create sites or import assets: use `scripts/seed_all.py` for a fresh installation. The full seed now includes the three foundation posts as well.

Each article is a separate Wagtail NewsPage marked **Blog post**, under the correct site homepage, with its own title, summary, topic, body, publication date and URL. View each site's journal at `/blog/`. The foundation journal also aggregates public programme articles.

Creation is transactional and site selection is validated before writing. Existing posts are preserved by parent page and slug, including edits, unpublished status and drafts. `--draft` applies only to newly created pages; publish reviewed drafts through Wagtail. Existing pages of another type using a seed slug cause an explicit error. A dry run makes no changes.

Edit future seed content in `apps/programmes/editorial.py` (programme articles) and `apps/programmes/foundation_blogs.py` (foundation articles). To change an article that already exists, edit it in Wagtail; rerunning the seed deliberately does not overwrite it. Publishing saves the article to the database search index; `python manage.py update_index` can rebuild the index when required.
