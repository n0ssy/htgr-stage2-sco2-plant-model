# HTGR Validation Matrix

Last updated: 2026-03-01

## 1) Validation Anchors and Gates

| Class | Anchor / Check | Metric | Acceptance Band | Source / Implementation |
|---|---|---|---|---|
| Cycle benchmark | Dostal-style recompression case | Thermal efficiency error | Within configured tolerance and converged | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/validation/dostal_validation.py` |
| Plant closure | Headline scenario energy closure | `energy_closure_rel` | `<= 0.005` | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py` strict gates |
| Cycle closure | Headline cycle closure | `cycle_energy_closure_rel` | `<= 0.005` | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py` strict gates |
| Optimization quality | Objective consistency | `objective_gap_rel` | `<= 0.01` | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py` + strict gates |
| Metadata integrity | Scenario tag completeness | Required fields present | 100% coverage | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py` strict gates |
| UQ reproducibility | Seeded rerun match | CI/percentiles exact match | Identical for fixed seed | `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py` strict gates |

## 2) Scenario Validation Set

1. `S0_BASE_30MW_OPONLY` (headline)
2. `S1_36MW_OPONLY` (power sensitivity)
3. `S2_30MW_FUELDISP` (boundary sensitivity)
4. `S3_36MW_FUELDISP` (optional combined sensitivity)

## 3) Current Gating Artifact

Gate status is exported to:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/audit_gate_results.json`

## 4) Known Validation Gaps

1. Single primary external benchmark anchor (Dostal) is still narrow for complete subsystem confidence.
2. Reactor safety-transient behavior is not validated via in-code transient simulation.
3. UQ space remains expandable to include additional cycle/thermal boundary variables.

## 5) Immediate Validation Expansion Backlog

1. Add second cycle anchor (alternate published operating point).
2. Add dedicated HX trend validation test set (geometry and dP monotonic checks).
3. Add process-accounting anchor comparison for both accounting boundaries.
4. Add documented acceptance bands per metric in alignment with RR confirmation.

