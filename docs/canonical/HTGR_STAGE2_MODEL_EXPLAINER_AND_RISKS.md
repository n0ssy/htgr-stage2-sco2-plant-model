# HTGR Stage-2 Model Explainer and Risk Register

Last updated: 2026-03-01  
Canonical pack snapshot: generated from `outputs/canonical_pack/` at run time

This document is the practical "what is happening" guide for the team.  
It explains:
1. what the model is solving,
2. what numbers are currently exported,
3. how to keep all teammate numbers synchronized,
4. which assumptions are false/risky and must be handled explicitly.

---

## 1) End Goal

Deliver a defensible HTGR Stage-2 evidence package that is:
1. physically consistent for the chosen scope,
2. reproducible and scenario-tagged,
3. aligned with RR deliverables and judging criteria,
4. easy to audit when numbers move between teammates, report, and slides.

Headline claim basis (locked):
1. HTGR-only scope.
2. Baseline = `30 MWth`.
3. Headline CO2 boundary = `fuel_displacement`.
4. Headline heat rejection representation = `fixed_boundary`.
5. Headline concept mode = `fuel_factory` with methanol-floor enforcement.

---

## 2) What the Plant Model Actually Does

## 2.1 Reactor Side (Boundary Model)
The reactor is represented as a thermal boundary condition:
1. fixed reactor thermal input (`Q_thermal`),
2. fixed helium hot/cold boundary temperatures and pressure.

It does not currently solve:
1. core neutronics,
2. transient reactor thermal-hydraulics,
3. 2D unit-cell safety physics.

Core entry points:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/coupled_solver.py`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/ihx.py`

## 2.2 sCO2 Cycle
The model solves a recompression Brayton cycle with real-gas CO2 properties:
1. turbine and compressors via isentropic efficiency models,
2. segmented HTR/LTR recuperators with pinch checks,
3. cycle-level feasibility checks (critical margin, TIT, pinch, energy closure).

Core files:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/sco2_cycle.py`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/turbomachinery.py`
3. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/components/recuperators.py`

## 2.3 Heat Exchanger Physics
HXs are segmented, enthalpy-based, pinch-constrained, with status diagnostics:
1. `CONVERGED`
2. `INFEASIBLE`
3. `NUMERICAL_FAIL`

Core file:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/hx/segmented_hx.py`

## 2.4 Heat Rejection Modes
Two solver modes exist:
1. `fixed_boundary` (headline): uses boundary assumptions for compressor inlet/cooling auxiliary.
2. `coupled_cooler` (sensitivity): uses explicit dry-cooler solve.

Core file:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/cycle/coupled_solver.py`

## 2.5 Process Allocation and CO2 FoM
After plant solve, net electric and waste heat are allocated to DAC/HTSE/grid via constrained optimization to produce process outputs and CO2 FoM.

CO2 accounting modes:
1. `fuel_displacement` (headline)
2. `operational_only` (sensitivity)

Core file:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/process/allocation.py`

## 2.6 Scenario and Reporting Pipeline
Canonical scenario pack generation and report-gate checks are in:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/run_tests.py`

---

## 3) Current Exported Numbers (Canonical Pack Snapshot)

Source:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/fom_summary_with_uncertainty.csv`

Read the latest values directly from:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/fom_summary_with_uncertainty.csv`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/scenarios/S2_30MW_FUELDISP.json`
3. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/uncertainty_summary.json`

Headline uncertainty snapshot is always read from `S2_30MW_FUELDISP` rows in canonical pack exports.

Source:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/uncertainty_summary.json`

---

## 4) How Report Numbers Must Be Updated and Synchronized

Team rule:
1. report and slide numbers must come only from scenario-tagged canonical exports.

Required files:
1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/scenarios/*.json`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/fom_summary_with_uncertainty.csv`
3. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/assumptions_register.csv`
4. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/outputs/canonical_pack/teammate_delta_table.csv`

Update workflow:
1. Regenerate canonical pack from code.
2. Use `S2_30MW_FUELDISP` for headline tables.
3. Use `S3_36MW_FUELDISP` for power sensitivity and `S0/S1` for boundary sensitivity.
4. Update teammate sections with delta-table mapping.
5. Reject any number without `scenario_id` and boundary metadata.

---

## 5) Key False or Risky Assumptions (Must Be Managed Explicitly)

| ID | Assumption (what people may think) | Reality | Impact | Required action |
|---|---|---|---|---|
| R1 | "Optimizer output is the true max-CO2 solution." | Not guaranteed without objective-consistency checks against deterministic screen. | Headline FoM may be materially understated or inconsistent. | Keep objective-gap gate active and block export on failure. |
| R2 | "Coupled cooler mode is validated enough for decision use." | Baseline coupled-cooler run currently returns infeasible plant energy closure at 40°C. | Detailed cooling sensitivity can mislead if presented as reliable. | Keep as appendix-only until closure and feasibility are fixed. |
| R3 | "Dostal pass means full model is validated." | Dostal validates cycle behavior only and currently with broad acceptance tolerance. | Overstated confidence if used as sole V&V claim. | Add more anchors and tighten acceptance criteria by metric. |
| R4 | "Reactor safety behavior is simulated in this model." | Reactor is boundary-driven; no transient core model yet. | Safety numbers can be misrepresented if treated as simulation outputs. | Label safety values as literature-benchmarked unless explicitly simulated. |
| R5 | "Teammate draft PDFs are valid final numeric sources." | They are reference/context only. | Inconsistent team numbers and audit risk. | Use canonical pack exports only for final numbers. |
| R6 | "Current uncertainty bounds cover total model uncertainty." | Current UQ mainly perturbs process intensities, not all major physics uncertainties. | Confidence interval may look more complete than it is. | Expand UQ variable set before final freeze. |
| R7 | "Assumption docs fully match runtime settings." | Some documented defaults can diverge from actual run configuration if not refreshed. | Report/code mismatch in audit. | Auto-refresh assumptions register from actual runtime config. |
| R8 | "Fuel-displacement FoM is boundary-free truth." | It depends on fuel EF and displacement assumptions. | Boundary confusion in presentations. | Always pair headline with explicit boundary statement and sensitivity mode. |

---

## 6) Known Technical Shortcomings (Current State)

1. Reactor fidelity gap:
- No 2D unit-cell surrogate integrated in simulation loop.

2. Allocation robustness:
- `MAX_CO2_NET` path likely suffers from optimization path dependence / local suboptimality in current setup.

3. Coupled cooler closure:
- Coupled mode can converge numerically but still fail plant-level energy closure constraints.

4. Validation depth:
- Single strong anchor (Dostal) is insufficient for full subsystem confidence claims.

5. UQ breadth:
- Current uncertainty treatment is useful but incomplete for full confidence reporting.

---

## 7) Immediate Development Priorities Before Freezing Final Numbers

Priority P0:
1. Keep fuel-factory methanol-floor enforcement and verify objective consistency under `fuel_displacement`.
2. Regenerate canonical pack and refresh all teammate-facing numbers.

Priority P1:
1. Improve coupled-cooler closure consistency and feasibility reporting.
2. Expand V&V anchors beyond Dostal.

Priority P2:
1. Expand UQ variable coverage.
2. Tighten assumptions-report consistency automation.

---

## 8) Practical "Do/Don't" for Team Members

Do:
1. Cite scenario-tagged values from canonical exports.
2. Keep headline claims on `S2_30MW_FUELDISP`.
3. Label every sensitivity with boundary mode and scenario ID.

Do not:
1. Copy raw numbers from draft teammate PDFs into final report tables.
2. Present `coupled_cooler` results as core headline evidence.
3. Treat fuel-displacement FoM as lifecycle-complete without boundary caveat.

---

## 9) Regeneration Commands

From repo root:

```bash
source venv/bin/activate
python run_tests.py
```

Canonical pack only:

```bash
source venv/bin/activate
python - <<'PY'
from run_tests import generate_stage2_canonical_pack
generate_stage2_canonical_pack()
PY
```

---

## 10) Companion Canonical Docs

1. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/sco2_plant/docs/canonical/CANONICAL_PROJECT_CONTEXT.md`
2. `/Users/stefioannidis/Documents/UCL/Y2/RR/copies/Corrected_Approach/teammate_resources/CANONICAL_TEAMMATE_REFERENCE.md`
