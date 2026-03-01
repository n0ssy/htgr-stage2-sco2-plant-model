# UCL Group 3 Final Report (Draft v2)
## Rolls-Royce Novel Fission Energy Project 2025-26

Team: Ariella Morris, Prim Mangkhalathanakun, Stefanos Ioannidis, Adithya Mendis, Mathias Tidball, Eima Miyasaka

## Acronyms
HTGR, HTTR, sCO2, RCBC, IHX, DAC, HTSE, PtL, TRISO, RCCS, DiD, LOFC, P-LOFC, D-LOFC, FoM, V&V, BEPU.

## 1. Introduction and Project Overview
Hard-to-abate sectors require energy vectors beyond direct electrification. Our project addresses this by integrating a High Temperature Gas-cooled Reactor (HTGR), a supercritical CO2 recompression Brayton cycle, direct air capture (DAC), and methanol synthesis into a water-independent Power-to-Liquids architecture.

The final headline case used throughout this report is the validated baseline scenario `S2_30MW_FUELDISP`: a 30.0 MWth reactor basis, fixed-boundary dry-cooling assumptions at 40C ambient, and a fuel-displacement carbon boundary. In this locked case, the plant is feasible and converged, produces 9.939 MWe net electrical output, and achieves 9,898 tCO2/year net reduction with a primary FoM of 329.9 tCO2/MWth/year.

A 36 MWth framing was explored during earlier project development to study dry-cooling penalty recovery; in this final report it is retained only as sensitivity context, not as the headline basis.

The report structure is: concept and down-selection (Sections 2-3), modelling and V&V (Sections 4-5), results/FoMs (Section 6), safety philosophy (Section 7), and lessons/teamwork/future work (Sections 8-9).

## 2. Concept Overview and Down-Selection
### 2.1 Design Constraint and Starting Point
The non-negotiable constraint was water-independent heat rejection. This eliminated solutions requiring continual external water replenishment for condenser duty. The starting reactor reference was HTTR-class helium-cooled operation, then integrated with an sCO2 conversion and process island able to use waste heat above 100C.

### 2.2 Application Selection (Pugh Matrix)
A structured Pugh process compared electricity export, hydrogen-only, and e-methanol pathways.

| Criterion | Weight | Electricity | H2 | E-Methanol (selected) |
|---|---:|---:|---:|---:|
| CO2 reduction potential | 5 | 0 | +1 | +2 |
| Water independence support | 5 | 0 | -1 | +1 |
| Transport/logistics practicality | 4 | 0 | -2 | +2 |
| Heat-integration potential | 3 | 0 | +1 | +2 |
| Total |  | 0 | -1 | +7 |

Decision logic: methanol provides transportable liquid fuel output and introduces a byproduct water loop that supports water-independence objectives.

### 2.3 Carbon Capture Selection (Pugh Matrix)
Solid sorbent DAC was selected against high-temperature liquid-solvent concepts due to regeneration-temperature compatibility with low-grade waste heat.

| Criterion | Weight | Liquid Solvent | Solid Sorbent (selected) |
|---|---:|---:|---:|
| Regeneration temperature compatibility | 5 | 0 | +2 |
| Fit with cycle waste heat | 5 | -1 | +2 |
| Energy-intensity suitability | 4 | 0 | +1 |
| Total |  | -1 | +5 |

### 2.4 Power Conversion Selection
Steam Rankine and sCO2 Brayton options were compared for dry-cooling feasibility and compactness.

| Criterion | Weight | Steam Rankine | sCO2 Brayton (selected) |
|---|---:|---:|---:|
| Dry-cooling feasibility | 5 | -2 | +2 |
| Turbomachinery compactness | 4 | 0 | +2 |
| Efficiency at HTGR outlet temperatures | 5 | 0 | +1 |
| Total |  | -2 | +5 |

Outcome: recompression sCO2 cycle selected as best fit to dry-cooling and integration constraints.

## 3. Integrated System Architecture
The final architecture is organized into three coupled zones.

1. Nuclear island: helium-cooled HTGR source with IHX as isolation barrier between primary nuclear loop and secondary process loops.
2. Power conversion: recompression sCO2 Brayton cycle producing net electrical output and controlled waste-heat streams.
3. Application island: DAC, HTSE, and methanol synthesis with internal energy allocation and no grid export in headline mode.

Thermal-cascade framing is retained: high-grade heat is used for power conversion; lower-grade heat is used for process needs (notably DAC regeneration) before final rejection. In the baseline solved case, headline process allocation is 2.982 MWe to HTSE, 1.988 MWe to DAC, 9.864 MWth heat to DAC, and 0.517 MWth heat to HTSE, with no electricity export.

This integrated architecture directly couples feasibility constraints (pinch, closure, supercritical margins) to process outputs, preventing detached subsystem optimization.

## 4. Modelling Development and Methodology
### 4.1 Modelling Philosophy and Fidelity
The modelling strategy prioritized system-level consistency over isolated local optima. A coupled plant solver was used so IHX duty, cycle state points, and process-allocation energy streams remain thermodynamically coherent.

Real-gas properties are computed with CoolProp. This is critical near the CO2 critical region where property gradients are steep and ideal-gas approximations are not acceptable.

### 4.2 sCO2 Plant Solver
The plant solution is built around iterative coupling of cycle, IHX, and cooling boundary assumptions with embedded feasibility checks. Recent implementation includes:
- deterministic operating-point seed search in bounded `(P_high, P_low, f_recomp)` space,
- moderate bounded tuning sequence for infeasible starts,
- convergence-reason tracing and per-iteration diagnostics,
- canonical fail-fast gating when required-feasible conditions are violated.

Segmented heat-exchanger treatment and pinch constraints are retained. Feasibility constraints are evaluated within the solve loop, not as post-hoc filtering.

Efficiency definitions used in this report:
- Thermal efficiency (`eta_thermal`): cycle gross electrical power over cycle heat input basis (`Q_in` internal to cycle model).
- Net efficiency (`eta_net`): plant net electrical power over reactor thermal basis (`Q_thermal`).

### 4.3 CO2 Accounting Method
#### Boundary Definition Box
Headline boundary (used in main text):

`fuel_displacement: CO2_net = CO2_displaced_fossil + CO2_grid - CO2_embodied - CO2_reemitted_synthetic (if neutrality disabled)`

Sensitivity boundary (reported separately):

`operational_only: CO2_net = CO2_DAC + CO2_grid`

In the headline case, grid export is disabled and neutrality is enabled, so fuel-displacement net reduction is set by displaced-fossil and embodied-product terms under solved allocation constraints.

Historical Jet-A equivalence assumptions are retained only for sensitivity framing and are not used to define the main headline FoM in this final draft.

## 5. Verification and Validation
### 5.1 Verification (Implementation Correctness)
Verification evidence includes:
- unit-level and integration-level checks for new feasibility-recovery logic,
- deterministic search behavior tests,
- fail-fast/override control-flow tests,
- range-guard and metadata persistence checks,
- consistency checks for generated diagnostics serialization.

### 5.2 Validation (Model-to-Reference)
The cycle validation anchor is the Dostal-style case in the committed runner. Recent authoritative run output reports 41.07% thermal efficiency against an expected 45.0% ± 5.0% acceptance band, and this gate passes.

### 5.3 Feasibility and Closure Evidence
For the headline baseline (`S2_30MW_FUELDISP`), all major gates pass:
- converged: true,
- feasible: true,
- plant energy closure: 0.435% (<0.5% tolerance),
- positive pinch/supercritical margins,
- canonical scenarios S0-S3 all feasible and converged in final run.

### 5.4 Limitations
- Headline mode uses fixed-boundary cooling assumptions; fully coupled-cooler mode is retained as sensitivity and is currently infeasible in the tested baseline ambient condition.
- Core transient safety results in Section 7 are literature/external-workstream tagged where not branch-reproduced.
- Uncertainty characterization uses the committed UQ summary artifact; this is not a complete BEPU campaign.

## 6. Results and Figures of Merit
### 6.1 Headline Plant Performance (`S2_30MW_FUELDISP`, fuel_displacement)

| Parameter | Value |
|---|---:|
| Reactor thermal power | 30.0 MWth |
| Net electrical output | 9.939 MWe |
| Thermal efficiency (`eta_thermal`) | 33.90% |
| Net efficiency (`eta_net`) | 33.13% |
| Energy closure (plant) | 0.435% |
| CO2 mass flow | 165.9 kg/s |
| Compressor inlet temperature | 50.0C |
| Turbine inlet temperature | 517.7C |
| IHX pinch margin | +13.00 K |
| HTR pinch margin | +1.66 K |
| LTR pinch margin | +2.82 K |
| Helium return margin | +10.74 K |
| Feasible / Converged | True / True |

### 6.2 Primary FoM (single headline boundary)
Headline basis is strictly fuel-displacement.

| Metric | Value |
|---|---:|
| Net CO2 reduction | 9,898 tCO2/year |
| Primary FoM | 329.9 tCO2/MWth/year |
| DAC capture rate | 44,468 tCO2/year |
| Hydrogen production | 627.3 t/year |
| Methanol production | 3245.3 t/year |

Uncertainty context (from committed UQ artifact, 120 samples):
- FoM mean: 331.6 tCO2/MWth/year
- p10/p50/p90: 302.7 / 331.5 / 360.8
- 95% interval: 288.6 to 377.9

This uncertainty reflects process-intensity perturbations around the locked baseline and should be read as model sensitivity context, not full technoeconomic project risk.

### 6.3 Sensitivity and Secondary FoMs
Canonical scenario summary (all feasible/converged in final run):

| Scenario | Basis | W_net (MWe) | FoM (tCO2/MWth/yr) | Feasible |
|---|---|---:|---:|---|
| S0_BASE_30MW_OPONLY | 30 MWth, operational_only | 9.939 | 1482.3 | Yes |
| S1_36MW_OPONLY | 36 MWth, operational_only | 12.101 | 1471.9 | Yes |
| S2_30MW_FUELDISP | 30 MWth, fuel_displacement (headline) | 9.939 | 329.9 | Yes |
| S3_36MW_FUELDISP | 36 MWth, fuel_displacement | 12.101 | 334.7 | Yes |

Secondary indicators:
- zero grid export in headline mode,
- dry-cooling auxiliary burden remains small relative to rejected heat,
- all headline feasibility margins non-negative.

## 7. Safety Philosophy
### 7.1 Defence in Depth
Safety strategy follows IAEA Defence-in-Depth principles with multiple independent barriers and passive safety emphasis. The report treats safety as a design driver, not a post-design add-on.

### 7.2 Inherent and Passive Features
The architecture relies on established HTGR safety characteristics: negative temperature feedback behavior, TRISO multi-layer fuel containment, and passive RCCS heat removal pathways.

### 7.3 Quantitative Safety Evidence and Provenance
Safety numbers are included with explicit provenance tags:
- P-LOFC / D-LOFC peak-temperature values: **external-workstream model outputs** (not reproduced by this branch commit).
- HTTR LOFC behavior references: **literature-backed** (JAEA/HTTR and related publications).
- TRISO integrity thresholds and DiD framing: **literature-backed**.

Any number without branch reproducibility is intentionally labeled as literature/external evidence to prevent provenance ambiguity.

### 7.4 Safety Limitations and Next Step
A branch-reproducible transient safety module is future work; meanwhile, safety quantification in this report should be interpreted as source-backed design evidence rather than branch-verified transient simulation output.

## 8. Challenges, Lessons Learned, and Team Structure
### 8.1 Professional Challenges
The central challenge was multi-disciplinary integration across reactor, cycle, process-allocation, and accounting workstreams. The team used RACI ownership, weekly sync cadence, and a shared assumptions log to prevent hidden interface drift.

### 8.2 Technical Challenges
The major technical challenge was solver robustness under tightly coupled constraints. Iterative divergence and feasibility drift were addressed by introducing bounded operating-point search, staged tuning controls, convergence diagnostics, and hard feasibility gates.

### 8.3 Lessons Learned
Three lessons were most important:
1. feasibility-gated modelling is more decision-useful than unconstrained optimization,
2. boundary definitions must be explicit early to avoid reporting drift,
3. reproducibility artifacts (scenario-tagged outputs + diagnostics) are essential for credible engineering communication.

### 8.4 Team Structure
Workstream ownership was maintained across six members with clear section responsibility and integration checkpoints. This enabled parallel development while keeping final interfaces coherent.

## 9. Novelty and Future Work
### 9.1 Novelty
The key novelty is system-level heat-quality integration: waste-heat utilization is treated as a design resource rather than solely a rejection burden. Combined with explicitly labeled fuel-displacement accounting and feasibility-gated optimization, this yields a defensible baseline FoM under explicit constraints.

### 9.2 Historical Context
The earlier 36 MWth framing remains useful as development history and sensitivity reference, but final headline claims are intentionally locked to the validated 30 MWth baseline.

### 9.3 Future Work
Priority next steps:
1. branch-reproducible safety transient model integration,
2. coupled-cooler sensitivity stabilization,
3. expanded uncertainty campaign (true BEPU-style optimistic/realistic/pessimistic envelopes),
4. higher-fidelity heat-rejection and off-design ambient analyses.

## References (condensed)
- Dostal et al. (2004), MIT-ANP-TR-100.
- IAEA INSAG-10, TECDOC references.
- JAEA HTTR LOFC public results.
- ANS 5.1 decay heat standard.
- Project branch artifacts listed in Appendix A.

## Appendix A: Evidence Artifacts (Branch-locked)
- `results_baseline.json`
- `co2_reduction_results.json`
- `outputs/canonical_pack/scenarios/*.json`
- `outputs/canonical_pack/uncertainty_summary.json`
- `outputs/diagnostics/headline_feasibility_trace.json`
