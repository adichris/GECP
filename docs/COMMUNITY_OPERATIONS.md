# Community operations — 11 October 2026

## Start or upgrade

Back up the database and media before replacing application code. Preserve `.env`, `db.sqlite3` and `media/` from the existing installation.

```sh
pip install -r requirements-dev.txt
npm ci
python manage.py migrate
python scripts/seed_all.py --domain localhost --port 8000
npm run build
python manage.py createsuperuser
python manage.py runserver 8000
```

Use the registered hostname and port. The local review copy was seeded on **8011** to avoid the old port-8000 server: use `--port 8011` and `runserver 8011` for this copy. New source installations default to 8000. The source archive excludes databases, accounts and environment secrets.

## Moderation

Create a named staff user, assign the relevant programme editor group, and create a ProgrammeMembership for that programme. Both permissions and membership are required. Run the seed after migration to add the community permissions to the editor groups. Superusers moderate the foundation and administer the whole network.

At `/operations/`, open Community → Threads or Comments. New records await review. Approve or hide selected contributions. Threads also support open/resolved status and locking. Reports are private; mark them Reviewed after handling. ModerationLog records moderation, status and withdrawal actions.

Withdrawn contributions cannot be republished through the bulk approval action and their visibility is read-only in the edit form. Hiding a parent comment also hides its replies. Locked topics reject new comments, including submissions from previously opened forms.

## Public features

- `/community/`: public topic search and category/status filters.
- `/community/new/`: discussions, questions, issues and suggestions.
- `/community/my-activity/`: own pending/published contributions and withdrawal.
- `/community/saved/`: private per-site article bookmarks.
- `/community/export/`: own community data for this site.
- `/accounts/register/`, `/accounts/login/`, `/accounts/password-reset/`: account flows.
- Blog articles: comments, one-level replies, reporting and 30-second refresh while visible.
- `/blog/feed/`: RSS. The foundation feed includes its registered programme network.

Users can resolve or reopen their own unlocked published topics. Moderators manage locks and may adjust status. Reports are not public. Withdrawal retains an administrative record; account deletion and retention requests need an administrator's controlled process.

## Email and abuse controls

Set EMAIL_BACKEND to `django.core.mail.backends.smtp.EmailBackend`, then configure EMAIL_HOST, EMAIL_PORT, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD, EMAIL_USE_TLS and DEFAULT_FROM_EMAIL. The console backend is for previews and does not deliver email. Verify a real password-recovery email before launch.

Database-backed rate limits are shared across workers. Authenticated activity is counted per account. Anonymous requests use a hashed client-address identifier. Behind a proxy, set TRUSTED_PROXY_IPS to the exact peer addresses seen by Django only when those proxies overwrite X-Real-IP. Otherwise clients behind the proxy share its anonymous quota. Arbitrary forwarded headers are not trusted.

The Nginx example rate-limits POST requests, including admin login. Run `python manage.py cleanup_community_limits` daily through your deployment scheduler to remove counters older than two days.

## Launch responsibilities

Configure real domains and site ports, HTTPS, PostgreSQL, durable media, tested backups, SMTP and named moderators. Review the privacy notice, retention schedule, community guidelines and current programme availability with the operating team.

Registration does not verify email ownership. Every contribution is reviewed before publication. This is a moderated public discussion service, not an identity-verified or instant support channel. Private messaging, video calls, payments, newsletters, MFA and placement/payroll workflows are not implemented.

Docker/PostgreSQL execution, external email delivery, real DNS/TLS and backup recovery have not been verified locally. No public deployment or external messages were sent in this task.


## Guest participation
Guests can start topics/issues and comment or reply without registration. Forms suggest a random name and emoji; the shuffle button replaces both, and visitors can edit the name and select an emoji. Published guest contributions are explicitly labelled Guest. Names are not unique or verified.

Ownership uses a secret in the server-side browser session, with only a keyed hash stored on contributions. Names never grant ownership. My guest activity shows pending submissions and permits withdrawal; authors can resolve unlocked published topics. Clearing cookies, session expiry or signing out can remove guest access. Signing in does not automatically transfer guest contributions to an account. Reports, bookmarks and account exports still require registration.

Guest submissions remain pending until approved, with CSRF, honeypot and IP-based rate limits. Changing names or clearing cookies does not reset IP limits. Existing member contributions remain linked to their accounts. Apply migrations and collect static files when upgrading.
