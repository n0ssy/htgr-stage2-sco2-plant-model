# HTGR Full Technical Audit

Last updated: 2026-03-01

## 1. Scope and Intent

This audit assesses whether the HTGR Stage-2 model is:
1. physically grounded for declared scope,
2. implemented correctly and consistently,
3. capable of producing report-defensible numbers with explicit uncertainty and traceability.

### In scope
1. HTGR thermal boundary representation.
2. sCO2 recompression cycle and component models.
3. IHX/HTR/LTR segmented HX implementation.
4. Heat-rejection treatment in headline and sensitivity modes.
5. Allocation optimizer and CO2 accounting boundaries.
6. Canonical output/export pipeline and report-gate controls.

### Out of scope
1. Full reactor neutronics/transient implementation.
2. New architecture outside the current HTGR+sCO2+process framework.

## 2. Physics Basis: What the Current Model Solves

## 2.1 HTGR boundary model
1. Reactor is represented by thermal boundary conditions (`Q_thermal`, helium in/out temperatures, pressure).
2. Helium flow is computed from duty and enthalpy drop via IHX-side model.
3. No core neutronics or time-dependent LOFC/D-LOFC physics are solved in this code.

Code anchors:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/coupled_solver.py`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/ihx.py`

Assessment: acceptable for HTGR Stage-2 plant-level scope if clearly disclosed as boundary-driven reactor representation.

## 2.2 sCO2 recompression cycle
1. Real-gas CO2 state equations via CoolProp.
2. Turbine/compressors modeled with isentropic efficiency.
3. HTR/LTR solved with segmented enthalpy balances and pinch checks.
4. Constraints include critical-point margins, TIT limit, positive work, and cycle closure.

Code anchors:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/sco2_cycle.py`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/turbomachinery.py`
3. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/properties/fluids.py`

Assessment: physically valid model form for system-level study.

## 2.3 Heat exchangers (IHX/HTR/LTR)
1. Segmented enthalpy marching with explicit pinch feasibility.
2. Optional friction-based dP mode.
3. Optional UA-limit closure to couple geometry to duty.

Code anchor:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/hx/segmented_hx.py`

Assessment: materially improved from pinch-only behavior; suitable for Stage-2 with explicit caveats on simplified UA correlations.

## 2.4 Heat rejection treatment
1. Headline mode: `fixed_boundary` (explicitly assumption-driven cooling parasitic and inlet condition).
2. Sensitivity mode: `coupled_cooler` with explicit fan power and closure constraints.

Code anchors:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/coupled_solver.py`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/dry_cooler.py`

Assessment: valid HTGR-only framing (headline independent of HRS design), with coupled-cooler retained as appendix sensitivity.

## 2.5 Allocation and CO2 accounting
1. Allocation constrained by electricity and heat balances.
2. HTSE heat requirement enforced when enabled.
3. CO2 accounting supports `operational_only` and `fuel_displacement`.
4. Unit conversion checks embedded for reporting integrity.

Code anchor:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py`

Assessment: model structure is appropriate, with strict objective-consistency checks now added.

## 3. Implementation Correctness Findings

Severity legend:
1. `P0` invalidates headline numbers.
2. `P1` materially biases sensitivity/confidence.
3. `P2` quality/auditability concern.

## 3.1 P0 findings addressed in this implementation cycle
1. Allocation optimizer could return suboptimal headline solutions under nonlinear SLSQP path dependence.
- Fix: deterministic coarse global screening mode for max-CO2 workflows + objective-consistency gap check.
- Location: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py`

2. Canonical exports could proceed without strict P0 validity gates.
- Fix: hard strict-interim gates and blocking failure behavior before canonical pack acceptance.
- Location: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py`

## 3.2 P1 findings addressed in this implementation cycle
1. Coupled-cooler solve could stop on cooler convergence before thermal source consistency was sufficiently settled.
- Fix: revised convergence logic in coupled mode requiring joint variable stabilization and cooler feasibility.
- Location: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/coupled_solver.py`

2. Assumption register mismatch risk (documented vs runtime segment counts).
- Fix: assumptions updated to reflect runtime defaults.
- Location: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py`

## 3.3 Remaining known limitations (not closed here)
1. Reactor model remains boundary-driven; no integrated 2D unit-cell/transient core model.
2. Validation remains anchored primarily to Dostal for cycle benchmark; broader anchors still required.
3. UQ currently emphasizes process-intensity uncertainty; full physics uncertainty envelope still expandable.

## 4. Numerical and Validation Status

Validation and trust requirements:
1. Cycle benchmark check (Dostal-style).
2. Plant and cycle closure checks.
3. Objective-consistency check against deterministic screen.
4. Scenario metadata completeness.
5. Seeded UQ reproducibility.

These are enforced via strict interim gate artifact:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/audit_gate_results.json`

## 5. Report-Readiness Requirements

A number is report-eligible only if:
1. it originates from scenario-tagged canonical outputs,
2. strict interim gates pass,
3. metadata includes scenario, boundary, and assumptions version,
4. teammate delta table is refreshed after latest pack generation.

Canonical sources:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/scenarios/*.json`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/fom_summary_with_uncertainty.csv`
3. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/teammate_delta_table.csv`

## 6. False Assumptions to Avoid in Team Narrative

1. "Dostal pass means whole-plant validation is complete." (false)
2. "Boundary-driven reactor model provides transient safety simulation outputs." (false)
3. "Manual teammate tables are equivalent to canonical exports." (false)
4. "Coupled cooler sensitivity can be promoted to headline without passing strict closure gates." (false)

## 7. Decision Summary

1. Headline remains `S0_BASE_30MW_OPONLY` under `operational_only` boundary.
2. Coupled cooler remains appendix sensitivity until all strict gates are satisfied in that mode.
3. Report freeze is permitted only from gate-passing canonical pack outputs.

