# docs/

| Folder | What lives here | Produced by |
| --- | --- | --- |
| `adr/` | Architecture Decision Records, numbered, never edited after acceptance (superseded instead) | `adr` |
| `analytics/` | The event design sheet (empty so far) | `analytics-events` |
| `api/` | Notes on the API contract; the contract itself is `api/openapi.yaml` | `openapi-spec` |
| `architecture/` | C4 diagrams, the ADR index with settled conflicts, design tenets, machine-readable plans | `architecture-diagram`, `tech-decision` |
| `design/` | High level design, data model, design system, screens, flows, motion | `high-level-design`, `data-model`, `design-system` |
| `performance/` | Measured performance records, one per task | `performance` |
| `postmortems/` | One per incident, dated (none so far) | `postmortem` |
| `privacy/` | Data map and the data protection impact assessment | `privacy-review` |
| `product/` | PRD, backlog, coverage matrix, estimate, open questions, proposed stories | `prd`, `backlog`, `estimate` |
| `progress/` | One short, committed progress file per task | `session-handoff` |
| `research/` | Spikes and surveys behind the ADRs (OCR engines, benchmark, hosting) | `spike` |
| `runbooks/` | One runbook per alert or procedure, such as `deploy.md` | `runbook` |
| `security/` | Auth design, permission matrix, threat model, security reviews | `auth`, `threat-model`, `vapt-report` |
| `superpowers/` | Written implementation plans and design specs | Superpowers |
| `templates/` | The blank templates the skills fill | Bearing |
| `testing/` | Test plan, cases, scenarios, risks, accuracy reports, acceptance audit | `test-cases`, `test-automation` |

Loose files: `decisions.md` (the technology decision log, one row per decision),
`DEBT.md` (the tech debt register), `spec-changes.md` (where `CONSTRAINTS.md`
overrides `spec.md`).

Read this first when new: `product/PRD.md` (what), `adr/` (why), `design/docket-hld.md` (how),
`testing/NOTASK-17-acceptance-audit.md` (what is proven today), `runbooks/deploy.md` (how to run it).
Several documents dated 2026-10-04 to 2026-10-06 were written before the code existed; where
they say the code is a scaffold, that was true on their date and the audit above is current.
