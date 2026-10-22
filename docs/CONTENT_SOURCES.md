# Retrieved GECP content and asset register

Retrieved for this build on 30 September 2026. The owner explicitly requested reuse of information, graphics and logos from other chats. Access covered the 50 most recent visible tasks plus the pinned task; this is not an assertion that the entire historical account archive was searched.

## Sources used

| Chat title | Conversation ID | Contribution | Treatment |
|---|---|---|---|
| List GECP Programmes | `6abbef08-84c8-83ea-b072-64398b61c09e` | Programme names, broad descriptions, proposed six pillars, modular platform direction | Registry working copy; six pillars remain a proposal |
| Write GECP Foundation Description | `6ab8119d-1e38-83ea-8a36-e1ed884cb0c8` | Foundation identity and educational purpose | Adapted into foundation introduction |
| GECP Foundation Logo Rationale | `6ab62770-92e8-83ea-b2c5-f891ee29ca01` | Uploaded foundation logo and tagline | Original image imported unchanged |
| CASMET Student Sales Team | `6aa34d69-a194-83ea-8f44-e7eaa7d1031d` | Official WWI/GECP logo uploads, CASMET positioning, WWS relationship, IVW extension, training and work-study workflow | WWI logo imported; hierarchy and planning records seeded; no live jobs or payment claims |
| GSEVS Logo | `6ab4022e-1938-83ea-bac8-63b346a8622f` | Uploaded GSEVS torch identity, brochure, nine service areas, manual outline | GSEVS logo imported; brochure retained as a reference asset |
| Develop GSEVS Programme | `6ab3f9a0-80f0-83ea-81cf-6e520b732fba` | Volunteer-service design context | Cross-check of terminology; no personal appointments published |
| Develop Organogram | `6ab669b5-f9d4-83ea-87d3-c05274dc959c` | GCCS units, learning promise and proposed governance | Initiative records seeded; GSEVS/TKRD coordination links explicitly proposed |
| RENGTECH -STC Partnership Proposal | `6ab7d5e8-7018-83e9-84c6-0f78d8cf16db` | User correction from Centre to Initiative; explicit GCCS relationship; proposed workshop pilot | Latest naming used; STC not listed as a confirmed partner; old artwork retained only as reference |
| Develop RENGTECH With Emphasis on Reverse Engineering Business | `6aace966-e304-83e9-a8cf-73d26aaea1c6` | Reverse Engineering & Innovation Hub concept | Proposed initiative description and future workflow requirements |
| WorkSafe Ghana and TRADESTART Funding Watch | `6a929727-3084-83ea-aadd-bc3466110eae` | WorkSafe/WWI relationship, TRADESTART support components | Broad programme structure only; dated grants and financial claims excluded |
| Elevator Pitch Opportunity Watch (EPOW) Monitoring System | `6a928b16-dbfc-83ea-bb01-f42833142005` | Opportunity-monitoring context and sample reporting fields | Requirements only; no historical calls represented as currently open |

## Original assets

The files in `seed_assets/` are byte-for-byte copies of attachments retrieved from the chats. `seed_assets/manifest.json` records original filenames, source chat IDs, source titles, intended use and SHA-256 hashes. Temporary retrieval paths are deliberately omitted.

- `gecp-logo.jpeg`: foundation identity from **GECP Foundation Logo Rationale**; used in the foundation header; an illustration is used in the hero.
- `wwi-logo.jpeg`: WWI identity supplied as official branding in **CASMET Student Sales Team**; used on WWI.
- `gsevs-logo.jpeg`: GSEVS torch identity from **GSEVS Logo**; used on GSEVS.
- `gecp-logo-alternative.jpeg`: an alternate supplied GECP treatment, retained for editorial comparison.
- `gsevs-brochure.jpeg`: reference graphic, not presented as a downloadable approved manual.
- `rengtech-brochure-previous-name.jpeg`: archival design with superseded “Centre” wording; available in the media library with an explicit planning-archive label.

Some chats mention generated Word/PDF files through content-reference placeholders. The available retrieval results provided text and the listed uploaded images, not those downloadable generated files. The build does not claim to contain inaccessible handbooks or brochures.

No independent logo was retrieved for PEC, SPIN, TRADESTART, ERAid, EVM, DRICD or TKRD. GCCS artwork was visible inside an older RENGTECH brochure, but no standalone original was returned. These sites keep text identities until originals are supplied or uploaded. No new official logo has been invented.

## Editorial reconciliation

- RENGTECH's latest explicit user naming is **Initiative**, superseding older **Centre** references.
- A branded site is not necessarily a top-level organisational programme. `Initiative.linked_site` lets the GCCS → RENGTECH relationship coexist with an independently branded RENGTECH site. The `Programme` model remains the site's platform registry and access scope.
- GCCS's GSEVS/TKRD coordination links come from a proposed organogram and are labelled as proposed, not settled governance.
- WWS is an initiative under WWI. CASMET is represented as its project; IVW is a planned activity/extension. If IVW becomes a separately managed project, move it to its own project record without splitting the codebase.
- Programme descriptions adapted from prior assistant writing remain editorial working copy. They are not evidence of active delivery, approved budgets, certified training or established partnerships.
- Personal names in draft appointment letters were not added to public staff pages. Historical grant amounts and deadlines were not imported as verified live opportunities.
- Brand colours for the recovered identities follow their visible navy, green, blue and gold palette. Exact hex values are implementation choices rather than a retrieved official brand specification.

## Reuse workflow

`seed_gecp` loads `apps/programmes/catalogue.py` and then `import_gecp_assets` and `enrich_gecp`. It does not overwrite an existing programme, page or logo. The asset import can also be run independently. Edit approved site content in Wagtail after initial seeding; do not rerun a destructive content reset.

## Expanded media and contact reconciliation

The public media library includes the six recovered originals and one conceptual illustration. Brochures and alternative branding are marked as planning archives; their text is not treated as current operational information. The retrieved images are not evidence of completed projects or confirmed partnerships.

The user selected **P.O. Box AN 29512, Accra** in this task. The telephone +233244736051 comes from the Career Pathways Overview chat; info@gecpfoundation.org appears in GECP materials. No unverified social accounts were invented.

### Generated illustration

File: `seed_assets/learning-together-illustration.png`. Mode: built-in image generation. It depicts conceptual learning, not actual participants. The image is labelled accordingly.

Final creative brief: Create a premium editorial illustration of a Ghanaian adult learning community, with three young adults and an older woman mentor working together on a small solar prototype at a table in a warm courtyard. Use a painterly, photograph-inspired collage style, natural green and warm earth tones, wide 3:2 composition, no text and no logos. Show intergenerational learning and practical collaboration without implying a real GECP event.

Only assets returned by the available chat retrieval were imported; this is not a claim that the entire ChatGPT Library has been accessed.
