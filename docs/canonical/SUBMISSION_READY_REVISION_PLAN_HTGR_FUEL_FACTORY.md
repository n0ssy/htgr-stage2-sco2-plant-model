# Submission-Ready Revision Plan (HTGR Stage-2, Fuel-Factory Headline)

## Status
- Document type: standalone execution lock (non-destructive)
- Scope: HTGR-only, fuel-factory headline
- Canonical assumptions version: `v3_fuel_factory_headline`
- Headline scenario: `S2_30MW_FUELDISP`

## Purpose
This document is the single execution spec for taking the current model + draft to final RR submission quality. It does not overwrite legacy planning documents; it references canonical outputs and enforces report gates.

## RR Deliverables Alignment
References:
- `source docs/RR-UES_Final_Deliverables_Guidance.pdf`
- `source docs/Rolls Royce Fission Energy Project 25-26.pdf`

Required RR evidence themes and how this plan satisfies them:
1. Modelling method clarity:
- Sections 2-3 rewritten from solver-implemented architecture and equations.
2. Validation and verification:
- Dostal + one additional anchor class + process analytic checks + consistency checks.
3. Assumptions and limitations transparency:
- Assumptions register with justification + RR alignment fields.
- Limitations register with impact and mitigation.
4. Feasible FoMs with confidence bounds:
- Scenario-tagged FoMs and seeded uncertainty summary.
5. Auditability:
- Every report number mapped to scenario, boundary, and source field.

## Locked Policy Decisions
1. Headline concept: `fuel_factory`.
2. Headline CO2 boundary: `fuel_displacement`.
3. Headline product behavior: methanol floor enforced.
4. Thermal basis: 30 MWth headline, 36 MWth sensitivity only.
5. Heat rejection headline mode: `fixed_boundary`; coupled cooler remains sensitivity evidence.
6. Safety section: external workstream evidence, not integrated transient solver output this cycle.

## Scenario Roles (Unchanged IDs)
1. `S2_30MW_FUELDISP`: headline.
2. `S3_36MW_FUELDISP`: power sensitivity.
3. `S0_BASE_30MW_OPONLY`: accounting boundary sensitivity.
4. `S1_36MW_OPONLY`: accounting + power sensitivity.

## Assumptions That Must Be Explicitly Stated and Justified
These must be present in report text and canonical outputs:
1. `fuel_displacement` is a project-level avoided-emissions FoM, not audited inventory reporting.
2. Fuel emission factor and displacement factor are assumptions with uncertainty treatment.
3. Headline cooling is a fixed boundary condition, not HRS design certification.
4. Reactor model is boundary-condition driven for this cycle (no full transient core coupling).
5. Unified energy-closure tolerance is 0.005 for solver/report consistency.
6. UQ is seeded 40-sample for reproducibility and schedule fit.

## Required Canonical Artifacts
All artifacts must be generated from model code, not manual entry:
1. `outputs/canonical_pack/report_number_map.csv`
2. `outputs/canonical_pack/validation_matrix.csv`
3. `outputs/canonical_pack/limitations_register.csv`
4. `outputs/canonical_pack/assumptions_register.csv`
5. `outputs/canonical_pack/audit_gate_results.json`
6. `outputs/canonical_pack/canonical_pack_index.json`

## Report Number Traceability Rule
Every report-facing metric must include:
1. `scenario_id`
2. `co2_accounting_mode`
3. `source_file`
4. `source_field`
5. `source_assumptions_version`

## Execution Checklist

### Phase 1: Freeze and Reframe
1. Freeze canonical source set in `outputs/canonical_pack/`.
2. Ensure headline references in draft point to `S2_30MW_FUELDISP`.
3. Add boundary statement in main text:
- headline is project FoM (avoided emissions), not inventory claim.

### Phase 2: Methods + Results Rebuild
1. Rebuild Sections 2-3 from implemented architecture and constraints.
2. Rebuild Section 4.3 equations for boundary modes.
3. Regenerate Section 6 tables from canonical exports only.

### Phase 3: Defensibility Upgrade
1. Keep Dostal anchor.
2. Add one additional validation anchor class with acceptance band.
3. Include process analytic checks and accounting consistency checks.
4. Include seeded 40-run uncertainty summary for headline scenario.

### Phase 4: Teammate Section Alignment
1. Sections 1, 4.3, 6, 8, 9: replace stale values with canonical values.
2. Section 7: keep as external safety stream with source-provenance table.

### Phase 5: Submission Gates
Block freeze if any of the following fail:
1. Headline scenario is not `S2_30MW_FUELDISP`.
2. Any report number missing required metadata fields.
3. Validation matrix missing added anchor class.
4. Wording implies audited inventory claim for headline.
5. Any stale number not matching canonical exports.

## Acceptance Criteria (Submission Ready)
1. Headline claim uses `S2_30MW_FUELDISP` only.
2. Every numeric claim in Sections 1, 4.3, 6, 8, 9 is scenario-tagged and traceable.
3. Assumptions are visible, justified, and RR-aligned.
4. Limitations are explicit with impact and mitigation.
5. Validation goes beyond Dostal and is tabulated.
6. Canonical pack gates pass with no failures.

## Ownership and Handoff Notes
1. This file is the execution lock for parallel sessions.
2. Any session updating numbers must regenerate canonical pack first.
3. Any report edit without scenario-tagged source mapping is non-compliant.
4. If assumptions change, bump assumptions version and regenerate all mapped artifacts.
