# Canonical Project Context (HTGR Stage-2)

Last updated: 2026-03-01

This is the single canonical reference for project scope, assumptions, scenario IDs, teammate input usage, and reporting rules.

Companion deep-dive (model behavior, outputs, and risk register):
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/docs/canonical/HTGR_STAGE2_MODEL_EXPLAINER_AND_RISKS.md`

## 1) What Is Authoritative

Use source priority in this order.

1. RR project scope and deliverables docs:
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/source docs/Rolls Royce Fission Energy Project 25-26.pdf`
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/source docs/RR-UES_Final_Deliverables_Guidance.pdf`

2. Model outputs generated from code (scenario-tagged):
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/`

3. Locked team policy docs:
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/AI_ONBOARDING.md`
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/TASKS_TBC.md`
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/PARALLEL_SESSION_LEDGER.md`

4. Teammate documents are reference-only unless their values are explicitly imported into scenario-tagged outputs.

## 2) Scope Locks (Do Not Override Without RR Confirmation)

1. Team scope: HTGR only.
2. Headline FoM boundary: `operational_only`.
3. Baseline reactor case: `S0_BASE_30MW_OPONLY` (30 MWth).
4. 36 MWth is sensitivity only (`S1_36MW_OPONLY`).
5. `fuel_displacement` is sensitivity only (`S2_30MW_FUELDISP`, optional `S3_36MW_FUELDISP`).
6. Headline HTGR results use `heat_rejection_mode="fixed_boundary"`; detailed cooler remains sensitivity/appendix.

## 3) What We Actually Need From Teammate Resources

Only the following are needed, and only for these purposes.

1. M3 safety files:
- Use for safety narrative structure, accident-case framing (LOFC/D-LOFC), and literature citations.
- Do not use draft safety temperatures/numbers as final unless reproduced or benchmarked in model outputs.

2. M5 process file:
- Use technology intensity ranges and provider references (DAC and HTSE) as input assumptions.
- Do not use fixed manual allocation splits as final values.

3. M6 research file:
- Use CO2 accounting frameworks, baseline/project boundary logic, and conversion factor references.
- Do not use manual arithmetic outputs directly in report tables.

4. FoM/safety draft report PDFs:
- Use section style and narrative flow only.
- Replace all provisional numbers with scenario-tagged exports from `/outputs/canonical_pack/`.

## 4) Non-Canonical Content Policy

A document is non-canonical if any of the following are true:

1. It contains untagged numbers (no scenario ID).
2. It mixes boundary modes without labels.
3. It reports manual calculations where code-generated outputs exist.
4. It predates locked scope decisions above.

Non-canonical docs must be treated as archive/reference only.

## 5) Canonical Scenario IDs and Usage

1. `S0_BASE_30MW_OPONLY`: headline reporting scenario.
2. `S1_36MW_OPONLY`: power sensitivity.
3. `S2_30MW_FUELDISP`: accounting-boundary sensitivity.
4. `S3_36MW_FUELDISP`: optional combined sensitivity.

All reported values must include at least:
- `scenario_id`
- `co2_accounting_mode`
- `heat_rejection_mode`
- `source_assumptions_version`

## 6) Team Synchronization Rule

Use only model exports from `/outputs/canonical_pack/` in slides/reports.

Required bundle:
1. `canonical_pack_index.json`
2. `scenarios/*.json`
3. `fom_summary_with_uncertainty.csv`
4. `assumptions_register.csv`
5. `teammate_number_reconciliation.csv`
6. `teammate_delta_table.csv`
7. `architecture_compliance_matrix.csv`
8. `limitations_register.csv`
9. `constraint_margin_table.csv`
10. `equation_sheet.md`

## 7) File Organization Rules

1. Keep active project context in this file only.
2. Keep historical/draft context in:
- `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/docs/archive/`
3. Keep RR source-of-truth docs only in `source docs/`.
4. If new teammate documents arrive, extract needed assumptions into canonical outputs and archive raw files.

## 8) Update Procedure (Mandatory)

For any new assumption or number:

1. Add/verify in model config or scenario input.
2. Re-run scenario generation.
3. Confirm tags and conversion checks pass.
4. Update canonical pack artifacts.
5. Update this file only if scope/policy changed.
