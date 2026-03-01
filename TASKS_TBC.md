# Tasks TBC (Research -> Plan -> Implement)

This backlog is the coordination point for all parallel AI sessions.

## Status Legend
- `TODO`: not started
- `IN_RESEARCH`: gathering evidence
- `IN_PLAN_REVIEW`: plan drafted, awaiting lock
- `IN_IMPLEMENTATION`: coding active
- `IN_VALIDATION`: testing and evidence packaging
- `DONE`: complete and documented
- `BLOCKED`: waiting on dependency/input

## Active Workstreams
| ID | Task | Status | Owner Session | Dependencies | Deliverables |
|---|---|---|---|---|---|
| T001 | Dual CO2 accounting API and logic (`operational_only` + `fuel_displacement`) | DONE | current | none | `process/allocation.py` updates + smoke test |
| T002 | Scenario-tagged exports and report-gate metadata | DONE | current | T001 | updated `run_tests.py` metadata fields |
| T003 | Canonical pack generator (`S0/S1/S2/S3`) | DONE | current | T001,T002 | `outputs/canonical_pack/*` |
| T004 | Teammate number reconciliation extraction from PDFs | DONE | current | T003 | `teammate_number_reconciliation.csv` |
| T005 | Delta table old vs new teammate values | DONE | current | T003,T004 | `teammate_delta_table.csv` |
| T006 | Architecture compliance + limitations register | DONE | current | T003 | `architecture_compliance_matrix.csv`, `limitations_register.csv` |
| T007 | Uncertainty summary for headline FoM | DONE | current | T003 | `uncertainty_summary.json`, FoM summary table |
| T008 | End-to-end runtime benchmark and optimization (reduce long run time) | TODO | unassigned | T003 | run-time profile + parameter tuning plan |
| T009 | RR meeting question pack refresh from latest model outputs | TODO | unassigned | T003,T005 | updated teammate-facing question doc |
| T010 | Add automated regression checks for scenario tags + conversion checks | TODO | unassigned | T003 | CI-like script or local gate checklist |

## Planning Protocol (Mandatory Before Major Changes)
1. `IN_RESEARCH`: collect code evidence + literature references.
2. `IN_PLAN_REVIEW`: draft implementation plan with interfaces, tests, edge cases.
3. Lock assumptions and scenario IDs.
4. Move to `IN_IMPLEMENTATION` only after plan lock.

## Immediate Next Actions
1. Profile and optimize runtime of the full canonical pack.
2. Add stricter parsing filters to reduce noisy teammate extraction rows.
3. Add automated regression script to rerun S0-S3 and compare drift bounds.
