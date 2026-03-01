# Revised Draft (Submission-Ready v2)

This file provides report-ready replacement text aligned to canonical model outputs and RR deliverable expectations. It preserves teammate-owned sections where possible and focuses major rewrite effort on Sections 2 and 3.

Canonical source set used:
1. `outputs/canonical_pack/report_number_map.csv`
2. `outputs/canonical_pack/fom_summary_with_uncertainty.csv`
3. `outputs/canonical_pack/assumptions_register.csv`
4. `outputs/canonical_pack/validation_matrix.csv`
5. `outputs/canonical_pack/audit_gate_results.json`
6. `outputs/canonical_pack/uncertainty_summary.json`
7. `outputs/canonical_pack/canonical_pack_index.json`

## Section 1 - Introduction and Project Overview (targeted update)
The global energy transition presents one of the most significant engineering challenges of our generation. Hard-to-abate sectors such as aviation, shipping, and heavy freight remain difficult to decarbonize through direct electrification alone. This report presents a water-independent, nuclear-enabled Power-to-Liquids system in which a High Temperature Gas-cooled Reactor (HTGR) is coupled to a supercritical CO2 recompression Brayton cycle, direct air capture (DAC), high-temperature steam electrolysis (HTSE), and methanol synthesis.

The locked headline case used consistently in this final report is `S2_30MW_FUELDISP` under the `fuel_displacement` boundary with `fuel_factory` concept mode. For this validated headline case, the model converges to a feasible plant at 30.0 MWth with 9.628 MWe net output, 32.85% thermal efficiency, 32.09% net efficiency, and 30,364 tCO2/year net reduction, corresponding to a primary figure of merit of 1012.1 tCO2/MWth/year.

For clarity, this headline value is a project-level avoided-emissions Figure of Merit under the fuel-displacement boundary, not an audited corporate GHG inventory claim. Operational-only results and 36 MWth cases are retained as sensitivity evidence.

The report proceeds as follows: concept down-selection and architecture (Sections 2-3), modelling development and V&V (Sections 4-5), results and figures of merit (Section 6), safety philosophy (Section 7), and team structure, challenges, and future work (Sections 8-9).

## Section 2 - Concept Overview and Down-Selection (full rewrite)
### 2.1 Design Objective and Constraints
The design objective was to maximize defensible annual CO2 reduction per reactor thermal input while preserving engineering feasibility under HTGR-only scope and dry-cooling-compatible operation. This immediately made three decisions first-order design variables rather than post-processing choices:
1. Process objective definition (DAC-max vs fuel-factory product-constrained).
2. Carbon accounting boundary (operational-only vs fuel-displacement).
3. Heat rejection representation for headline feasibility (fixed-boundary vs fully coupled cooling model).

To prevent claim drift, scenario roles were locked before final reporting:
1. `S2_30MW_FUELDISP` is the headline case.
2. `S3_36MW_FUELDISP` is power sensitivity.
3. `S0_BASE_30MW_OPONLY` and `S1_36MW_OPONLY` are boundary sensitivities.

### 2.2 Application Selection and Product Pathway Logic
The application down-selection compared three pathways: electricity export, hydrogen-only, and integrated e-methanol production. The e-methanol pathway remained preferred because it best matched the team vision and delivered the strongest integrated score across:
1. Potential decarbonization impact in hard-to-abate transport fuel use.
2. Compatibility with high-temperature nuclear-assisted process integration.
3. Transport and logistics practicality relative to pure hydrogen export.
4. Opportunity to convert otherwise low-value rejected heat into useful process duty.

For Stage-2 finalization, this selection was formalized in solver constraints rather than narrative preference. The model now enforces a minimum methanol production floor in headline mode, ensuring headline results cannot be achieved by DAC-only allocation behavior.

### 2.3 Carbon Capture and Conversion Chain Selection
Solid sorbent DAC was retained due to compatibility with low-to-moderate temperature heat and modular integration potential. HTSE was retained as the hydrogen production route to align with high-temperature process integration and reduced electrical intensity relative to low-temperature electrolysis routes in this architecture context. Methanol synthesis was retained as the chemical product pathway linking captured CO2 and produced H2.

The implemented fuel-factory constraint set for headline mode is:
1. `concept_mode = fuel_factory`
2. `co2_accounting_mode = fuel_displacement`
3. `enforce_min_meoh_output = True`
4. `min_meoh_t_yr = 8833` for the 30 MWth headline case

This ensures concept-policy consistency between system architecture, optimization behavior, and reported figures of merit.

### 2.4 Headline Boundary Choice and Justification
Two accounting boundaries are still computed, but one is designated headline and the other sensitivity:
1. Headline: `fuel_displacement` in `S2`.
2. Sensitivity: `operational_only` in `S0` and `S1`.

This choice was made to align the headline with the team’s fuel-factory concept and intended end-use decarbonization claim. To maintain defensibility, boundary dependence is made explicit in tables and metadata, and uncertainty/sensitivity around boundary assumptions is reported.

## Section 3 - Integrated System Architecture (full rewrite)
### 3.1 Architecture Definition
The final integrated architecture is represented as three coupled zones:
1. Nuclear island: HTGR thermal source with an intermediate heat exchanger (IHX) isolating reactor coolant from the power-conversion loop.
2. Power conversion island: recompression sCO2 Brayton cycle generating net electric output and rejected heat streams.
3. Process island: DAC, HTSE, and methanol synthesis receiving constrained electricity/heat allocation from plant outputs.

The architecture is solved as a coupled thermodynamic and allocation problem, not as disconnected subsystem calculations.

### 3.2 Energy and Information Flow
The model enforces the following sequence:
1. Solve plant thermodynamic state (cycle + IHX + boundary-mode heat rejection representation).
2. Compute available electrical and thermal resources for process allocation.
3. Solve constrained allocation for DAC/HTSE/methanol under scenario policy.
4. Compute annual CO2 metrics under selected accounting boundary.
5. Apply strict gate checks before accepting canonical outputs.

Key gating checks include convergence, feasibility, closure tolerances, policy consistency, and metadata completeness.

### 3.3 Governing Constraints (Implemented)
The coupled solution is constrained by:
1. Supercritical margins near the CO2 critical point.
2. Pinch constraints in IHX/HTR/LTR.
3. Turbine inlet temperature cap.
4. Positive net plant output.
5. Plant energy closure threshold `<= 0.005` relative.
6. Allocation electricity and heat balances.
7. Optional HTSE heat requirement enforcement (enabled for headline/sensitivity runs here).
8. Headline methanol production floor in fuel-factory cases.

For headline conditions, heat rejection is represented in `fixed_boundary` mode to preserve HTGR-only scope while maintaining thermodynamic closure. Coupled cooler behavior remains available as sensitivity evidence but does not determine headline FoM.

### 3.4 Scenario Architecture Policy
The architecture-policy map is:
1. `S2_30MW_FUELDISP`:
- 30 MWth
- fuel_factory
- fuel_displacement
- methanol floor active
- headline
2. `S3_36MW_FUELDISP`:
- 36 MWth
- fuel_factory
- fuel_displacement
- methanol floor active
- power sensitivity
3. `S0_BASE_30MW_OPONLY` and `S1_36MW_OPONLY`:
- DAC-max style allocation
- operational-only accounting
- boundary sensitivity

This map removes ambiguity about which scenario is used for which claim.

## Section 4 - Modelling Development and Methodology (targeted updates)
### 4.1 and 4.2
Keep existing text structure. Add one sentence at end of 4.2:
"Final feasibility acceptance requires simultaneous convergence, feasibility, policy-consistency, and closure checks, and these are exported in machine-readable gate artifacts."

### 4.3 CO2 Accounting Methodology (replace subsection)
Two boundary modes are implemented and explicitly tagged in outputs:
1. `operational_only`: net effect from modeled onsite operation and process allocation only.
2. `fuel_displacement`: project-level avoided-emissions framing using a fossil comparator and displacement factor assumptions.

Headline policy for this report is:
1. Headline scenario: `S2_30MW_FUELDISP`.
2. Headline boundary: `fuel_displacement`.
3. Boundary sensitivities: `S0`, `S1` operational-only and `S3` power-scaled fuel-displacement.

Main-text headline equation:
`Net_CO2_fuel_displacement = CO2_displaced_fossil + CO2_grid - CO2_embodied - CO2_reemitted_synthetic(if neutrality disabled)`

In this report configuration, no-grid-export policy is active in headline mode (`CO2_grid = 0`), neutrality condition is enabled, and output metadata includes the accounting mode, boundary statement, and assumption version.

Key assumptions (must remain explicit):
1. Headline is project avoided-emissions FoM, not audited inventory accounting.
2. Fuel EF and displacement factor are assumption-driven and sensitivity/UQ-governed.
3. Unit conversions are validated via explicit conversion checks before export.

## Section 5 - Verification and Validation (targeted updates)
### 5.1 Verification
Keep existing structure, but replace any statement implying 0.1% universal closure with:
"Cycle and plant-level closure tolerances are enforced at 0.5% relative threshold (`0.005`) for Stage-2 gating, with reported achieved residuals below this limit in headline runs."

### 5.2 Validation Against Reference Case
Keep Dostal text and update with current values:
1. Dostal-style anchor: model thermal efficiency `41.10%` against reference `45.0% ± 5.0%`, pass.
2. Added secondary cycle anchor: `40.35%` within accepted band `[30%, 55%]`, pass.

### 5.3 Feasibility Evidence
Replace headline sentence with:
"The final authoritative run demonstrates headline baseline `S2_30MW_FUELDISP` converged and feasible, with all canonical scenarios `S0-S3` converged and feasible under strict metadata and policy gates."

## Section 6 - Results and Figures of Merit (replace all tables and scenario-role text)
### 6.1 Plant Performance Summary
The headline performance case is `S2_30MW_FUELDISP` with `fuel_displacement` accounting.

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

### 6.2 Primary Figure of Merit (headline)
| Metric | Value |
|---|---:|
| Net CO2 reduction (fuel_displacement headline) | 30,364.1 tCO2/year |
| Primary FoM | 1012.1 tCO2/MWth/year |
| DAC capture | 15,192.4 tCO2/year |
| Hydrogen production | 1,924.4 t/year |
| Methanol production | 9,955.4 t/year |

Uncertainty context from canonical seeded UQ (`40` samples, seed `20260301`):
1. Mean FoM: `1004.9` tCO2/MWth/year.
2. P10/P50/P90: `892.2 / 1007.9 / 1220.1`.
3. 95% interval: `690.2` to `1238.5` tCO2/MWth/year.

### 6.3 Secondary Figures of Merit (scenario matrix)
| Scenario | Basis | Net power (MWe) | FoM (tCO2/MWth/year) | Feasible |
|---|---|---:|---:|---|
| S2_30MW_FUELDISP | 30 MWth, fuel_displacement | 9.628 | 1012.1 | Yes |
| S3_36MW_FUELDISP | 36 MWth, fuel_displacement | 11.464 | 1004.3 | Yes |
| S0_BASE_30MW_OPONLY | 30 MWth, operational_only | 9.628 | 3014.8 | Yes |
| S1_36MW_OPONLY | 36 MWth, operational_only | 11.464 | 3025.6 | Yes |

Secondary conclusions:
1. Feasibility is maintained across all canonical scenarios.
2. 36 MWth results are sensitivity only.
3. Boundary mode strongly changes FoM magnitude and interpretation, so scenario tags and boundary labels are mandatory for all claims.

## Section 7 - Safety Philosophy (minimal update only)
Keep teammate text and structure. Add one explicit scope sentence at the start of Section 7.4:
"Safety transient values in this section are reported as external-workstream evidence with source provenance and are not direct outputs of the integrated plant solver used for Sections 2-6."

## Section 8 - Challenges, Lessons Learned, Team Structure (minimal update)
Keep current text but apply two edits:
1. Replace references to headline lock on `S0_BASE_30MW_OPONLY operational_only` with `S2_30MW_FUELDISP fuel_displacement`.
2. Replace any statement of universal `0.1%` closure requirement with the implemented Stage-2 gate `0.5%` relative tolerance and achieved headline residual below that threshold.

## Section 9 - Novelty and Future Work (minimal update)
Keep current narrative. In future work, add:
1. Extend validation anchors beyond current two cycle/process classes.
2. Progress from boundary-level reactor treatment toward higher-fidelity HTGR reactor-side coupling.
3. Expand uncertainty campaign after submission freeze.

## Appendix 4.3 - sensitivity note update
Replace the opening note with:
"Appendix 4.3 documents boundary and comparator derivations for sensitivity interpretation. Headline claims in the main report use `S2_30MW_FUELDISP` under the project avoided-emissions (`fuel_displacement`) framing with explicit assumption tagging."

## References - targeted additions for Sections 2-6
Add these references to support methodology language:
1. Dostal, V. (2004) *A Supercritical Carbon Dioxide Cycle for Next Generation Nuclear Reactors*. MIT PhD thesis.
2. ASME V&V 20 standard page for V&V framing.
3. RR project brief and final deliverables guidance documents (local source docs in repository).

