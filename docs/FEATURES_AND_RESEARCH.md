# Feature review and research — 11 October 2026

The platform remains a Django/Wagtail modular monolith. This review covers the requested programme, publishing, participation and community workflows, not every possible organisational business process.

| Area | Implemented |
| --- | --- |
| Network | Foundation and 11 branded programme sites, hierarchy, strict hostname routing, scoped content and permissions |
| Publishing | Wagtail revisions, richer programme homepages, news/events/opportunities/resources, 25 blog articles and seven library assets |
| Discovery | Site/network search, programme and blog filters, sitemaps, media library |
| Appearance | Light/dark/system preferences, operating-system change detection, per-site persistence, brand-aware light palette, responsive layouts and reduced motion |
| Participation | Programme-specific forms, contact and applications, consent, CSRF, honeypot, replay protection, shared rate limits, email receipts and staff alerts |
| Events | Upcoming/past listings, per-event and per-site iCalendar (.ics) downloads |
| Sharing and SEO | Open Graph/Twitter tags, schema.org JSON-LD (Organization, Event, BlogPosting), sitemap in robots.txt |
| Staff portfolios | Staff profiles and portfolio items, optional project links, programme-scoped team directory, private items, admin hiding and metadata-stripped images |
| Submissions admin | Search, staff notes, bulk status actions and injection-safe CSV export |
| Community | Discussions/questions/issues/suggestions, comments, one-level replies, moderation, reporting and periodic updates |
| Issue handling | Open/resolved state, author resolution/reopening and moderator locks |
| Accounts | Registration, sign-in/out, password changes/recovery and host-local sessions |
| Reader tools | Per-site bookmarks and RSS; drafts/private pages excluded |
| User controls | Own activity, withdrawal from public view and per-site data export |
| Moderation | Programme-scoped queues, approval/hiding and audit records |
| Operations | Docker/Compose, PostgreSQL configuration, static asset build, proxy example, health endpoint, migration/seeding and CI |

## Research decisions

- [Django security](https://docs.djangoproject.com/en/5.2/topics/security/): informs CSRF, escaping, HTTPS and authentication throttling. Public contributions remain plain text, writes require CSRF-protected POSTs, and request counters are shared through the database.
- [Django authentication](https://docs.djangoproject.com/en/5.2/topics/auth/default/): built-in authentication, validation and password recovery underpin the account flows. Recovery links use the registered current site.
- [Django deployment checklist](https://docs.djangoproject.com/en/5.2/howto/deployment/checklist/): unique secrets, explicit hosts, HTTPS and durable services remain production launch requirements.
- [Wagtail private pages](https://docs.wagtail.org/en/v7.4/advanced_topics/privacy.html): comment endpoints, bookmarks, feeds and discovery exclude private/unpublished pages.
- [MDN prefers-color-scheme](https://developer.mozilla.org/en-US/docs/Web/CSS/Reference/At-rules/@media/prefers-color-scheme): system mode follows the browser media query; explicit visitor choices take precedence.
- [OWASP XSS prevention](https://cheatsheetseries.owasp.org/cheatsheets/Cross_Site_Scripting_Prevention_Cheat_Sheet.html): untrusted public text is escaped and no executable attachments are accepted.

## Scope and operating requirements

Every new contribution awaits review. A real moderation team and a retention policy are required. Password recovery needs SMTP delivery. Registered usernames are not verified identities; email verification and MFA are not implemented.

Private chat, video, payments, bulk newsletters, placement matching, payroll and ticketing need further product/provider decisions. They are not presented as working features. Container startup, a live PostgreSQL database, DNS/TLS, SMTP delivery and backup recovery still need verification on the deployment host. See COMMUNITY_OPERATIONS.md for setup and boundaries.
