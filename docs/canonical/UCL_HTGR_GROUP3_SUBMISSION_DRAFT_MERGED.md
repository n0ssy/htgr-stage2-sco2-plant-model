# UCL HTGR Group 3 Final Report (Merged Submission Draft)

## Team Members
Ariella Morris (TL), Prim Mangkhalathanakun, Stefanos Ioannidis, Adithya Mendis, Mathias Tidball, Eima Miyasaka

## Acronyms
ANS - American Nuclear Society  
DAC - Direct Air Capture  
D-LOFC - Depressurised Loss of Forced Cooling  
DiD - Defence-in-Depth  
HTGR - High Temperature Gas-cooled Reactor  
HTSE - High-Temperature Steam Electrolysis  
HTTR - High Temperature Engineering Test Reactor  
IAEA - International Atomic Energy Agency  
IHX - Intermediate Heat Exchanger  
INSAG - International Nuclear Safety Advisory Group  
JAEA - Japan Atomic Energy Agency  
LOFC - Loss of Forced Cooling  
RCCS - Reactor Cavity Cooling System  
RPV - Reactor Pressure Vessel  
TRISO - Tri-structural Isotropic fuel particle

## Section 1 - Introduction and Project Overview
The global energy transition presents one of the most significant engineering challenges of our generation. Hard-to-abate sectors such as aviation, shipping, and heavy freight remain difficult to decarbonize through direct electrification alone. Addressing this gap demands clean, energy-dense synthetic fuels produced at scale without dependence on water-intensive cooling or externally constrained process energy.

This report presents a water-independent, nuclear-enabled Power-to-Liquids architecture in which an HTGR is coupled to a supercritical CO2 recompression Brayton cycle, DAC, HTSE, and methanol synthesis.

The locked headline case used consistently in this final report is `S2_30MW_FUELDISP` under the `fuel_displacement` boundary with `fuel_factory` concept mode. For this validated headline case, the model converges to a feasible plant at 30.0 MWth with 9.628 MWe net output, 32.85% thermal efficiency, 32.09% net efficiency, and 30,364.1 tCO2/year net reduction, corresponding to a primary figure of merit of 1012.1 tCO2/MWth/year.

This headline value is a project-level avoided-emissions Figure of Merit under a fuel-displacement comparator boundary, not an audited corporate GHG inventory claim. Operational-only accounting and 36 MWth results are retained as sensitivity evidence.

The report proceeds as follows: concept down-selection and architecture (Sections 2-3), modelling development and V&V (Sections 4-5), results and figures of merit (Section 6), safety philosophy (Section 7), and team lessons and future work (Sections 8-9).

## Section 2 - Concept Overview and Down-Selection
### 2.1 Design Objective and Constraint
The design objective was to maximize defensible annual CO2 reduction per unit reactor thermal input while preserving engineering feasibility under HTGR team scope and water-independent operation. This made three decisions first-order design variables rather than post-processing choices:
1. Process objective mode (`dac_max` versus `fuel_factory`).
2. CO2 accounting boundary (`operational_only` versus `fuel_displacement`).
3. Heat-rejection representation for headline feasibility (`fixed_boundary` versus coupled-cooler sensitivity).

To prevent claim drift, scenario roles were locked before final reporting:
1. `S2_30MW_FUELDISP` - headline claim.
2. `S3_36MW_FUELDISP` - power sensitivity.
3. `S0_BASE_30MW_OPONLY` and `S1_36MW_OPONLY` - accounting-boundary sensitivities.

### 2.2 Application Selection (Pugh Matrix Outcome)
The application down-selection compared electricity export, hydrogen, and e-methanol pathways. E-methanol remained the selected route due to the strongest combined score in carbon impact relevance, logistics practicality, and integrated heat-use potential.

For Stage-2, this selection was translated into hard model behavior rather than narrative preference: headline scenarios enforce minimum methanol output so the solution cannot collapse to DAC-only allocation while still being presented as a fuel-factory concept.

### 2.3 Carbon Capture and Power-Cycle Selections
Solid sorbent DAC was retained over high-temperature solvent routes due to compatibility with available low-to-moderate grade heat and modular implementation. Recompression sCO2 Brayton conversion was retained over steam Rankine due to dry-cooling compatibility, compactness, and good fit with HTGR outlet temperature conditions.

### 2.4 Headline Boundary Choice
Two accounting boundaries are retained in the model, but their report roles are explicit:
1. Headline: `fuel_displacement` (`S2`).
2. Sensitivity: `operational_only` (`S0`, `S1`).

The headline boundary is chosen to align with the team’s fuel-factory concept. To preserve defensibility, boundary dependence is always presented with scenario tags, assumptions, and uncertainty context.

## Section 3 - Integrated System Architecture
The final architecture is split into three coupled zones:
1. Nuclear island: HTGR thermal source with IHX as the physical isolation barrier.
2. Power conversion island: recompression sCO2 cycle delivering net electrical output and rejected-heat streams.
3. Process island: DAC, HTSE, and methanol synthesis with constrained allocation under no-grid-export headline policy.

Thermal-cascade logic is retained: high-grade heat supports power conversion, while lower-grade heat supports process duty before final rejection.

### 3.1 Coupled Solution Flow
The implemented sequence is:
1. Solve plant thermodynamic state (cycle + IHX + heat-rejection mode).
2. Compute available electrical and thermal resources for process use.
3. Solve constrained allocation across DAC, HTSE, and methanol synthesis.
4. Compute annual CO2 metrics under selected accounting boundary.
5. Apply strict report gates before canonical export.

### 3.2 Governing Constraints
The final solution is accepted only when all major constraints pass together:
1. Convergence and feasibility status are true.
2. Plant and cycle closure are within threshold (`<= 0.005` relative).
3. Pinch and thermal margins remain non-violating.
4. Allocation power/heat balances close.
5. Headline policy checks pass (`fuel_factory`, methanol floor active, correct scenario metadata).

### 3.3 Headline and Sensitivity Policy
For report consistency:
1. `S2` is the sole headline scenario.
2. `S3` is scalability sensitivity.
3. `S0`/`S1` quantify accounting-boundary sensitivity.

This structure keeps a singular headline FoM while still showing feasibility and interpretation sensitivity around boundary assumptions.

## Section 4 - Modelling Development and Methodology
### 4.1 Modelling Philosophy and Fidelity
The modelling approach prioritizes thermodynamic and allocation consistency across subsystems rather than isolated component optimisation. Real-gas properties are evaluated with CoolProp to capture near-critical CO2 behavior where idealized assumptions are unreliable.

### 4.2 Coupled Solver and Feasibility Logic
The plant solve uses deterministic bounded operating-point search, moderate recovery tuning for infeasible starts, per-iteration diagnostics, and fail-fast gating for infeasible headline states. Feasibility constraints are checked during solve progression.

Final acceptance requires simultaneous convergence, feasibility, policy consistency, and closure compliance. All gates are exported as machine-readable audit artifacts.

### 4.3 CO2 Accounting Methodology
Two accounting boundaries are implemented and explicitly tagged:
1. `operational_only`: onsite operational/process basis.
2. `fuel_displacement`: project-level avoided-emissions comparator basis.

Headline policy in this report:
1. Headline scenario: `S2_30MW_FUELDISP`.
2. Headline boundary: `fuel_displacement`.
3. Sensitivity boundaries: `S0`, `S1` operational-only and `S3` power sensitivity.

Main-text headline equation:
`Net_CO2_fuel_displacement = CO2_displaced_fossil + CO2_grid - CO2_embodied - CO2_reemitted_synthetic(if neutrality disabled)`

In the locked headline configuration, grid export is zero and neutrality is enabled.

Key assumptions are explicitly recorded in canonical outputs, including fuel EF, displacement factor, methanol floor, closure tolerance, and boundary statement policy.

## Section 5 - Verification and Validation
### 5.1 Verification
Verification focused on implementation correctness and control-flow integrity:
1. deterministic scenario behavior and reproducibility,
2. feasibility and metadata propagation,
3. fail-fast and override pathway control,
4. scenario-tagged JSON diagnostics for traceability.

### 5.2 Validation Anchors
Validation evidence includes more than a single benchmark:
1. Dostal-style cycle anchor: model thermal efficiency 41.10% versus 45.0% +/- 5.0% acceptance, pass.
2. Secondary cycle anchor: model efficiency 40.35% within accepted [30%, 55%] band, pass.
3. Process analytic closure checks (DAC intensity, HTSE intensity, methanol stoichiometry), all pass.
4. Boundary-consistency check from identical plant state, pass.

### 5.3 Feasibility and Gate Evidence
The final authoritative run demonstrates:
1. headline scenario `S2_30MW_FUELDISP` converged and feasible,
2. plant and cycle closure thresholds passed,
3. objective consistency and methanol-floor policy checks passed,
4. all canonical scenarios (`S0-S3`) converged and feasible under required gates.

## Section 6 - Results and Figures of Merit
### 6.1 Plant Performance Summary (Headline: S2_30MW_FUELDISP)
| Metric | Value |
|---|---:|
| Reactor thermal power | 30.0 MWth |
| Net electrical power | 9.628 MWe |
| Thermal efficiency | 32.85% |
| Net efficiency | 32.09% |
| Plant energy closure | 0.377% |
| CO2 mass flow | 162.5 kg/s |
| Compressor inlet temperature | 50.0 C |
| Turbine inlet temperature | 520.0 C |
| HTR pinch margin | +0.98 K |
| IHX pinch margin | +13.37 K |
| LTR pinch margin | +3.02 K |
| Helium return margin | +0.92 K |
| Feasible / Converged | True / True |

### 6.2 Primary Figure of Merit (Headline)
| Metric | Value |
|---|---:|
| Net CO2 reduction (fuel_displacement headline) | 30,364.1 tCO2/year |
| Primary FoM | 1012.1 tCO2/MWth/year |
| DAC capture | 15,192.4 tCO2/year |
| Hydrogen production | 1,924.4 t/year |
| Methanol production | 9,955.4 t/year |

Uncertainty context for headline FoM (seeded UQ, 40 samples):
1. Mean: 1004.9 tCO2/MWth/year.
2. P10/P50/P90: 892.2 / 1007.9 / 1220.1.
3. 95% interval: 690.2 to 1238.5 tCO2/MWth/year.

### 6.3 Secondary Figures of Merit (All Feasible and Converged)
| Scenario | Basis | Net Power (MWe) | FoM (tCO2/MWth/year) |
|---|---|---:|---:|
| S2_30MW_FUELDISP | 30 MWth, fuel_displacement (headline) | 9.628 | 1012.1 |
| S3_36MW_FUELDISP | 36 MWth, fuel_displacement | 11.464 | 1004.3 |
| S0_BASE_30MW_OPONLY | 30 MWth, operational_only | 9.628 | 3014.8 |
| S1_36MW_OPONLY | 36 MWth, operational_only | 11.464 | 3025.6 |

Secondary conclusions:
1. Feasibility is maintained across all canonical scenarios.
2. 36 MWth values are sensitivity context only.
3. Boundary mode strongly affects FoM magnitude and interpretation, so scenario tags and boundary labels are required for all reported values.

## Section 7 - Safety Philosophy
Safety is integral to our HTGR design. The architecture follows IAEA Defence-in-Depth and relies on inherent reactor physics, robust fuel containment, and passive cooling. Quantitative transient values in Section 7.4 are presented as external-workstream evidence with source provenance; they are not direct outputs of the integrated plant solver used for Sections 2-6.

### 7.1 Defence-in-Depth Framework
The safety philosophy is structured around IAEA INSAG-10 Defence-in-Depth across five levels: prevention, detection/control, engineered safety systems, accident management, and emergency response. Multiple barriers must fail simultaneously before release can occur.

### 7.2 Inherent Safety Characteristics
Two mechanisms anchor the safety case:
1. negative temperature coefficient of reactivity, causing self-limiting power response,
2. large graphite-core thermal inertia, slowing transient evolution.

Both are consistent with HTGR/HTTR evidence cited in Section 7 references.

### 7.3 TRISO Fuel and Passive Cooling
TRISO fuel barriers and passive RCCS heat removal are central to the safety philosophy and support the project’s water-independent heat rejection requirement.

### 7.4 Safety Transient Analyses (External Workstream Evidence)
Three Python-based transient models were developed in the safety workstream:
1. pressurised LOFC bounding case,
2. depressurised LOFC case,
3. natural-circulation sensitivity case.

Reported values and figures are provenance-labeled and should be interpreted as safety-workstream evidence rather than integrated solver output.

## Section 8 - Challenges, Lessons Learned, and Team Structure
### 8.1 Professional Challenges
A principal challenge was coordinating multidisciplinary workstreams (reactor physics, thermodynamics, process modeling, and carbon accounting) without assumption drift. The team response included a versioned assumptions log and clear workstream ownership to maintain traceability and consistency.

### 8.2 Technical Challenges
The key technical challenge was nonlinear behavior near the CO2 critical region and propagation of coupling errors through the heat-exchanger network. The mitigation strategy was modular verification, staged integration, and strict feasibility/closure gating in the coupled workflow.

### 8.3 Team Structure
The team maintained defined workstream ownership with regular synchronization and shared evidence artifacts. This structure reduced duplication and improved consistency across model development, reporting, and safety narrative integration.

## Section 9 - Novelty and Future Work
### 9.1 Novelty
The primary novelty is integrated use of heat quality across generation and process pathways with explicit feasibility gating and scenario-tagged FoMs. The approach converts rejected heat from a pure penalty into a constrained process resource.

### 9.2 Future Work
Priority next steps:
1. integrate additional validation anchors and broader external benchmark comparisons,
2. expand uncertainty campaign beyond current submission baseline,
3. progress from boundary-level reactor representation toward higher-fidelity reactor-side coupling,
4. continue maturing coupled cooling sensitivity capability for appendix-level evidence.

## Assumptions and Limitations (Main-Body Summary)
| Item | Current treatment | Why acceptable now | Next-step upgrade |
|---|---|---|---|
| Headline accounting boundary | `fuel_displacement` project FoM | Aligns with fuel-factory concept and is explicitly labeled | Add RR-specified boundary preference if provided |
| Cooling representation in headline | `fixed_boundary` | HTGR-only scope, thermodynamic closure maintained | Improve coupled cooling fidelity in sensitivity appendix |
| Reactor-side fidelity | Boundary-condition thermal source | Appropriate for this cycle scope | Add higher-fidelity reactor-side coupling |
| UQ depth | Seeded 40-sample campaign | Reproducible and schedule-compatible | Expand sample size and input uncertainty space |
| Safety integration | External workstream evidence | Preserves traceability and avoids overclaiming integration | Add tighter coupling path in future stage |

## References
### Core project and methodology references
1. Rolls-Royce. *University Energy Societies – Final Deliverables Guidance* (11/02/2025).
2. Rolls-Royce. *Rolls Royce Fission Energy Project 2025-2026*.
3. Dostal, V. (2004). *A Supercritical Carbon Dioxide Cycle for Next Generation Nuclear Reactors*. MIT PhD Thesis.
4. ASME. *V&V 20 Standard* (Verification and Validation in CFD and Heat Transfer Modelling).

### Section 7 safety references (teammate workstream)
1. IAEA (1996) INSAG-10 Defence in Depth in Nuclear Safety.
2. JAEA (2024) HTTR safety demonstration updates.
3. Takamatsu et al. (2014) HTTR LOFC experiments and validation.
4. OECD/NEA (2024) LOFC project references.

## Appendix 4.3 Note
Appendix 4.3 should be retained for detailed derivations and comparator logic. Main-body headline claims in this report use `S2_30MW_FUELDISP` under project avoided-emissions (`fuel_displacement`) framing with explicit scenario and assumption tagging.
