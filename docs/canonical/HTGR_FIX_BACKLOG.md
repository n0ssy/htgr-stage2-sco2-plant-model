# HTGR Fix Backlog (Post-Audit)

Last updated: 2026-03-01

## Priority Definitions

1. `P0`: must pass before headline numbers are report-eligible.
2. `P1`: high-impact fidelity and confidence improvements.
3. `P2`: quality and long-horizon capability improvements.

## P0 (must complete before report data freeze)

1. Allocation optimizer robustness for max-CO2 workflows.
- Status: closed in current cycle.
- Implementation: deterministic screening + objective consistency diagnostics.
- Files: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py`

2. Objective-consistency rejection of suboptimal accepted solutions.
- Status: closed in current cycle.
- Implementation: `objective_gap_rel` and `objective_consistency_passed` with fail-on-gap behavior.
- Files: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py`

3. Hard canonical report gates.
- Status: closed in current cycle.
- Implementation: strict interim gate checks + export block + `audit_gate_results.json`.
- Files: `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py`

## P1 (high-impact, next wave)

1. Coupled-cooler energy-closure reliability improvements.
- Status: partial (iteration logic improved; further calibration still needed).
- Next: tighten coupled-mode closure diagnostics and acceptance behavior.

2. Validation expansion beyond single benchmark anchor.
- Status: open.
- Next: add at least one additional independent anchor and subsystem-level acceptance matrix.

3. Assumptions-to-runtime consistency automation.
- Status: partial.
- Next: auto-derive assumption register from runtime scenario config to eliminate drift risk.

4. UQ coverage expansion.
- Status: open.
- Next: include additional cycle and boundary uncertainties in seeded propagation.

## P2 (quality and extensibility)

1. Machine-generated issue register refresh utility.
- Status: open.
- Next: script issue register generation from gate and audit findings.

2. Structured diagnostics standardization across all scenario exports.
- Status: open.
- Next: stabilize schema for optimizer, cycle, and gate diagnostics.

3. Reactor-fidelity roadmap integration.
- Status: open.
- Next: staged 2D unit-cell surrogate integration with explicit benchmark references.

## Execution Sequence

1. Run strict gates and regenerate canonical pack.
2. Refresh teammate delta table from new scenario exports.
3. Update report/deck values only from canonical pack artifacts.
4. Freeze assumptions version used for final report tables.

