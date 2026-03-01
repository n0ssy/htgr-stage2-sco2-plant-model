# Revised Draft Submission Update Guide (Canonical-Linked)

## Purpose
Use this guide to update the revised report draft so every claim is aligned with canonical model outputs and RR expectations.

## Canonical Sources (Do Not Bypass)
1. `outputs/canonical_pack/report_number_map.csv`
2. `outputs/canonical_pack/fom_summary_with_uncertainty.csv`
3. `outputs/canonical_pack/assumptions_register.csv`
4. `outputs/canonical_pack/limitations_register.csv`
5. `outputs/canonical_pack/validation_matrix.csv`
6. `outputs/canonical_pack/audit_gate_results.json`
7. `outputs/canonical_pack/canonical_pack_index.json`

## Mandatory Headline Framing
1. Headline scenario is `S2_30MW_FUELDISP`.
2. Headline FoM boundary is `fuel_displacement`.
3. Add this statement near first headline metric mention:
- "This headline value is a project-level avoided-emissions Figure of Merit under the fuel-displacement boundary, not an audited corporate GHG inventory claim."

## Section Update Actions

### Section 1 (Executive Summary)
1. Replace old S0/operational-only headline references with S2 headline values from `report_number_map.csv`.
2. Keep 30 MWth as headline basis; label 36 MWth only as sensitivity.
3. Include scenario tags beside key numbers in internal drafting notes.

### Sections 2-3 (Methods and Modelling)
1. Describe architecture as implemented: HTGR boundary + sCO2 cycle + constrained allocation + accounting boundary switch.
2. Include assumptions selected for headline from `assumptions_register.csv`.
3. State feasibility/closure policy: tolerance `0.005` and strict gate logic.

### Section 4.3 (CO2 Accounting)
1. Rewrite equations to match implemented modes:
- `operational_only` for sensitivity only.
- `fuel_displacement` for headline.
2. Remove ambiguous inventory-equivalence phrasing.
3. Add boundary and assumption dependencies (fuel EF, displacement factor).

### Section 6 (Results)
1. Regenerate all tables from `report_number_map.csv` and `fom_summary_with_uncertainty.csv` only.
2. Include columns for:
- `scenario_id`
- `co2_accounting_mode`
- `headline_or_sensitivity`
3. Add uncertainty line for headline from `uncertainty_summary.json` via map entries.

### Section 7 (Safety)
1. Keep section as external workstream.
2. Add provenance table for each numeric safety claim (source + scope statement).
3. Do not present safety values as direct outputs of this solver.

### Sections 8-9 (Discussion and Conclusions)
1. Recompute all comparisons from canonical outputs only.
2. Add limitation impacts from `limitations_register.csv`.
3. Ensure recommendations reference current scope limits and next-step fidelity upgrades.

## Validation and Defensibility Inserts
1. Include validation table from `validation_matrix.csv` (Dostal + secondary cycle anchor + process analytic checks + boundary consistency).
2. Include pass/fail gate statement from `audit_gate_results.json`.
3. Include assumption transparency table from `assumptions_register.csv`.

## Pre-Submission Checklist
1. Every reported number appears in `report_number_map.csv`.
2. Every headline claim references `S2_30MW_FUELDISP`.
3. Boundary statement appears in summary and methods.
4. Validation includes more than Dostal.
5. Limitations are explicit and paired with mitigation.
6. No stale S0-headline wording remains.

## Freeze Rule
If any checklist item fails, the draft is not submission-ready and must not be frozen.
