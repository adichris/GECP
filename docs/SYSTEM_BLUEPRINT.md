# Programme systems blueprint

This maps the recovered planning material to extension points in the runnable MVP. Only the “implemented” column describes functioning software. The remaining columns are scoped backlog, not hidden or partially implemented functionality.

| Area | Implemented foundation | Next domain records | Workflow to implement |
|---|---|---|---|
| PEC / SPSOW | Programme site, opportunity pages, applications, resources | Counselling case, appointment, education plan, scholarship eligibility profile | Intake → consent → triage → booking → counselling → plan → follow-up |
| WWI / WWS / CASMET / IVW | Programme/initiative/project/activity hierarchy, applications, recovered WWI logo | Student profile, academic availability plan, employer, campaign, assignment, training result, verified work record, skills passport | Recruit → screen → train → match → supervise → verify → compensation review → record competencies |
| GCCS / CELL / Autodidacts’ Academy | Learning-unit catalogue, events, resources | Learning pathway, course, cohort, enrolment, assessment, learning portfolio | Discover → enrol → learn → evidence → feedback → progress |
| RENGTECH | GCCS affiliation, independent site, hub concepts, application intake | Equipment intake, job card, diagnosis, safety review, design/version, materials, work order, test record | Receive → assess ownership/suitability → diagnose → approve scope → repair/prototype → validate → document → hand over |
| SPIN | Talent/innovation content and initial enquiry route | Skills profile, evidence, project challenge, team membership | Profile → verify capabilities → discover challenge → collaborate → record outcomes |
| GSEVS / EPINet | Nine service areas, programme logo, application intake | Expert profile, competency, host request, assignment terms, vetting, matching, hours, feedback | Register → vet → onboard → match → agree assignment → deliver → evaluate → recognise |
| TRADESTART | Support-stream catalogue, intake and resources | Graduate profile, trade, enterprise, asset allocation, mentor relationship, market linkage, outcome | Assess → enterprise preparation → support decision → asset stewardship → mentor → follow-up |
| ERAid | Resource pages and partner association | Resource request, inventory, donor pledge, allocation, distribution acknowledgement | Request → review → source → allocate → deliver → confirm |
| EVM | News/media publishing and research-to-impact initiative | Series, episode, contributor, transcript, distribution metadata | Commission → produce → review → publish → distribute |
| DRICD / TKRD | Knowledge-service catalogue and resource library | Research brief, consented knowledge capture, interview, source, transcript, taxonomy, access licence | Scope → consent → collect → curate → review → preserve → share |
| EPOW / opportunity watches | Searchable opportunity pages, deadline rules, application intake | Source URL, verification date, eligibility, geographic fit, support type, reviewer, supersession history | Discover → verify primary source → classify → editorial review → publish → recheck → expire |
| Shared operations / MEAL | Admin permissions, site scope, project/activity status | Indicator, baseline, target, outcome observation, evidence, report | Define → collect → validate → review → report → learn |

## Shared design rules for subsequent modules

Use a single user identity and explicit programme memberships. Model permissions alone are insufficient for scoped access; filter querysets and validate parent/foreign-key choices in every new interface. Public application IDs must be checked against the current site and page visibility. Personal applicant/expert/student data must remain out of public page models and search indexes.

Keep business transitions in reusable application services with clear actor permissions, transaction boundaries and audit records. A text status field should not silently authorise payments, placements or safeguarding decisions. Add automated tests for invalid transitions and cross-programme access when each workflow is built.

Separate proposed partners from confirmed relationships. Add review/verification dates to externally sourced calls, and do not make historical chat summaries the source of truth for eligibility, deadlines or financial terms.

Continue using the modular monolith. Add programme-specific modules only as actual workflows require them. An API, task queue, notification service or object-storage backend should be introduced for a concrete integration or operational requirement.
