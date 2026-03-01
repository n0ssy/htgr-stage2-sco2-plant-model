Team Members:  
Ariella Morris (TL)

Prim Mangkhalathanakun

Stefanos Ioannidis

Adithya Mendis  
Mathias Tidball

Eima Miyasaka

### Acronyms:

(For Section 7)

**ANS** — American Nuclear Society

**D-LOFC** — Depressurised Loss of Forced Cooling

**DiD** — Defence-in-Depth

**HTGR** — High Temperature Gas-cooled Reactor

**HTTR** — High Temperature Engineering Test Reactor

**IAEA** — International Atomic Energy Agency

**INSAG** — International Nuclear Safety Advisory Group

**JAEA** — Japan Atomic Energy Agency

**LOFC** — Loss of Forced Cooling

**PyC** — Pyrolytic Carbon

**RCCS** — Reactor Cavity Cooling System

**RPV** — Reactor Pressure Vessel

**SCRAM** — Safety Control Rod Axe Man (emergency reactor shutdown)

**SiC** — Silicon Carbide

**TRISO** — TRi-structural ISOtropic (coated fuel particle)

# Section 1 - Introduction and Project Overview

The global energy transition presents one of the most significant
engineering challenges of our generation. Hard-to-abate sectors -
aviation, shipping, and heavy freight - contribute approximately 30% of
global energy-related emissions (Sharmina et al, 2020), yet remain
largely inaccessible to direct electrification. Addressing this gap
demands a fundamentally different approach: clean, energy-dense
synthetic fuels produced at scale, without dependence on constrained
resources.

This report presents a water-independent, nuclear-enabled
Power-to-Liquids system in which a High Temperature Gas-cooled Reactor
(HTGR) is coupled to a supercritical CO2 recompression Brayton cycle,
direct air capture (DAC), high-temperature steam electrolysis (HTSE),
and methanol synthesis.

The locked headline case used consistently in this final report is
`S2_30MW_FUELDISP` under the `fuel_displacement` boundary with
`fuel_factory` concept mode. For this validated baseline, the model
converges to a feasible plant at 30.0 MWth with 9.628 MWe net output,
32.85% thermal efficiency, 32.09% net efficiency, and 30,364.1
tCO2/year net reduction, corresponding to a primary figure of merit of
1012.1 tCO2/MWth/year.

This headline value is a project-level avoided-emissions Figure of Merit
under a fuel-displacement comparator boundary, not an audited corporate
GHG inventory claim.

Earlier 36 MWth framing is retained only as historical development
context and sensitivity evidence; it is not used as the headline final
result basis.

Every design decision, from power conversion selection to carbon
accounting methodology, was made through a documented,
assumption-tracked process underpinned by rigorous modelling and
independent verification and validation.

The report proceeds as follows: concept down-selection and architecture
(Sections 2-3), modelling development and V&V (Sections 4-5), results
and figures of merit (Section 6), safety philosophy (Section 7), and
team structure, challenges and future work (Sections 8-9).

# Section 2 - Concept Overview and Down-Selection

### 2.1 Design Objective and Constraint

The design objective was to maximize defensible net CO2 reduction while
preserving engineering feasibility under a strict water-independent heat
rejection requirement. This made cooling architecture, process
integration, and carbon accounting boundary definitions first-order
design choices rather than secondary checks.

### 2.2 Application Selection (Pugh Matrix)

The application down-selection compared electricity export, hydrogen,
and e-methanol pathways.

| Criterion | Weight | Electricity | H2 | E-methanol (selected) |
|---|---:|---:|---:|---:|
| CO2 reduction potential | 5 | 0 | +1 | +2 |
| Water-independence support | 5 | 0 | -1 | +1 |
| Transportability/logistics | 4 | 0 | -2 | +2 |
| Heat-integration potential | 3 | 0 | +1 | +2 |
| Total |  | 0 | -1 | +7 |

Decision: e-methanol provided the strongest combined score across carbon
impact, logistics practicality, and thermal-integration opportunity.

### 2.3 Carbon Capture and Power-Cycle Selections

Solid sorbent DAC was selected over high-temperature liquid-solvent
capture due to direct compatibility with low-grade heat. Recompression
sCO2 Brayton conversion was selected over steam Rankine due to dry
cooling feasibility, compactness, and integration with the HTGR outlet
temperature regime.

# Section 3 - Integrated System Architecture

The final architecture is split into three coupled zones: nuclear
island, power conversion island, and process island.

1. Nuclear island: HTGR thermal source with IHX as the physical
   isolation barrier.
2. Power conversion island: recompression sCO2 cycle delivering net
   electrical power and rejected-heat streams.
3. Process island: DAC, HTSE, and methanol synthesis under no-grid-export
   headline operation.

Thermal-cascade logic is retained: high-grade heat supports power
conversion, lower-grade heat supports process duty before final
rejection. This architecture converts what is typically treated as
low-value rejected heat into a productive CO2-reduction resource.

For final headline scenarios, allocation is constrained in fuel-factory
mode with an enforced minimum methanol output floor, preventing the
solution from collapsing to DAC-only operation while still being
presented as integrated fuel production.

# Section 4 - Modelling Development & Methodology

## 4.1 Modelling Philosophy and Fidelity

The modelling approach prioritizes thermodynamic consistency across
subsystems rather than isolated subsystem optimization. Real-gas
properties are evaluated with CoolProp to capture near-critical CO2
behavior where constant-property or ideal-gas assumptions are not
reliable.

## 4.2 Coupled Solver and Feasibility Logic

The plant solve uses a coupled iterative structure with embedded
feasibility gates:

- deterministic bounded operating-point seed search over
  `(P_high, P_low, f_recomp)`,
- staged moderate tuning for infeasible starts,
- per-iteration diagnostics and convergence-reason tagging,
- fail-fast gating for headline infeasibility and canonical feasibility
  enforcement.

Feasibility constraints are checked during solve progression, not only
as post-processing.

## 4.3 CO<sub>2</sub> Accounting Methodology

The net annual CO<sub>2</sub> calculation compares annual emissions in
the baseline scenario to those in the project scenario, using explicit
boundary labels to avoid ambiguity between accounting modes. To preserve
continuity with the legacy team draft, the original baseline/project/net
equation chain is retained in Appendix 4.3 as sensitivity/comparator
context.

#### **4.3.1 Baseline Scenario**

Two accounting boundaries are retained in the project, but only one is
used for headline claims in the main body:

- `fuel_displacement` (headline): includes displaced fossil-fuel
  comparator assumptions.
- `operational_only` (sensitivity): net reduction from modeled plant
  operation and on-site process allocation.

#### **4.3.2 Project Scenario**

Main-text equation (headline boundary):

`Net_CO2_fuel_displacement = CO2_displaced_fossil + CO2_grid - CO2_embodied - (CO2_reemitted_synthetic if neutrality disabled)`

For the locked headline case, grid export is zero by design and
neutrality is enabled in the accounting settings, so:

`Net_CO2_fuel_displacement = CO2_displaced_fossil - CO2_embodied = 30,364.1 tCO2/year`

#### **4.3.3 Net CO<sub>2</sub> Reduction**

Sensitivity equation (reported in Section 6.3 only):

`Net_CO2_operational_only = CO2_DAC + CO2_grid`

This mode is retained for sensitivity context and is not used as the
headline figure in the main report body.

#### **4.3.4 Key assumptions**

- The main-body headline is always `fuel_displacement`.
- The `operational_only` basis is shown only as sensitivity.
- Headline optimization is run in `fuel_factory` concept mode with a
  minimum methanol output floor enabled.
- kgCO2 and kgCO2e are treated as equivalent in this engineering-stage
  accounting pass.
- No-grid-export policy is applied in the headline scenario.
- Headline CO2 claims are reported as project-level avoided-emissions
  FoMs, not audited inventory claims.

# Section 5 - Verification and Validation

## 5.1 Verification

Verification focused on implementation correctness and control-flow
integrity:

- deterministic operating-point search behavior and repeatability,
- feasibility-recovery range guards and metadata persistence,
- fail-fast and override pathway control logic,
- JSON-serializable diagnostics for trace artifacts.

These checks were executed through unit-level and integration-level
tests in the branch workflow.

## 5.2 Validation Against Reference Case

The cycle reference validation remains the Dostal-style benchmark case.
The committed authoritative run reports 41.10% thermal efficiency
against a 45.0% +/- 5.0% acceptance band, and the validation gate
passes. Additional validation anchors include secondary cycle sanity-band
checks, process-intensity closure checks (DAC/HTSE/methanol), and
boundary-consistency checks from identical plant states under alternative
accounting boundaries.

## 5.3 Feasibility Evidence

The final authoritative run demonstrates:

- headline baseline (`S2_30MW_FUELDISP`) converged and feasible,
- plant energy closure within tolerance,
- objective-consistency and methanol-floor policy checks passed for the
  headline scenario,
- all canonical scenarios S0-S3 converged and feasible under required
  gating.

This provides a branch-reproducible feasibility basis for the results in
Section 6.

# Section 6 - Results & Figures of Merit

## 6.1 Plant Performance Summary

The headline performance case is the locked baseline
`S2_30MW_FUELDISP` with `fuel_displacement` accounting. The integrated
configuration is feasible and converged under the final authoritative
run.

Table 6.1 — Integrated Plant Performance

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

All electrical output remains on-site in headline mode, with no grid
export.

## 6.2 Primary Figure of Merit

Table 6.2 – Primary Figure of Merit

| Metric | Value |
|---|---:|
| Net CO2 reduction (fuel_displacement) | 30,364.1 tCO2/year |
| Primary FoM | 1012.1 tCO2/MWth/year |
| DAC capture | 15,192.4 tCO2/year |
| Hydrogen production | 1,924.4 t/year |
| Methanol production | 9,955.4 t/year |

The dominant sensitivity drivers include electrolyser efficiency
(electricity demand per unit hydrogen), DAC parasitic load (energy
required for CO<sub>2</sub> capture), and overall cycle efficiency
(heat-to-electric conversion performance). These parameters directly
affect total energy demand and, therefore, the calculated CO<sub>2</sub>
reduction and FOM.

Uncertainty context from the committed canonical UQ artifact (40
samples): FoM mean 1004.9 tCO2/MWth/year, p10/p50/p90 of 892.2 / 1007.9
/ 1220.1, and a 95% interval of 690.2 to 1238.5 tCO2/MWth/year.

## 6.3 Secondary Figures of Merit

Canonical sensitivity summary (all feasible and converged):

| Scenario | Basis | Net power (MWe) | FoM (tCO2/MWth/year) | Feasible |
|---|---|---:|---:|---|
| S2_30MW_FUELDISP | 30 MWth, fuel_displacement (headline) | 9.628 | 1012.1 | Yes |
| S3_36MW_FUELDISP | 36 MWth, fuel_displacement | 11.464 | 1004.3 | Yes |
| S0_BASE_30MW_OPONLY | 30 MWth, operational_only | 9.628 | 3014.8 | Yes |
| S1_36MW_OPONLY | 36 MWth, operational_only | 11.464 | 3025.6 | Yes |

Secondary conclusions:
- Feasibility is maintained across all four canonical scenarios.
- 36 MWth results are retained as sensitivity context only.
- Operational-only values are sensitivity-only and not used as headline
  claims in the main report.
- Boundary mode strongly affects FoM magnitude and interpretation, so
  scenario tags and boundary labels are required on all reported values.

# Section 7 - Safety Philosophy

Safety is integral to our HTGR design. The architecture follows the IAEA
Defence-in-Depth framework and relies on inherent reactor physics,
robust fuel containment, and passive cooling. Quantitative transient
values in Section 7.4 are explicitly provenance-labeled to distinguish
branch-reproduced outputs from external-workstream evidence.

## 7.1 Defence-in-Depth Framework

The safety philosophy is structured around IAEA INSAG-10
Defence-in-Depth, comprising five independent levels: **(1) Prevention**
through conservative design margins; **(2) Detection and Control** via
instrumentation, negative temperature feedback, and control rod systems;
**(3) Engineered Safety Systems** including TRISO fuel barriers and the
passive RCCS; **(4) Accident Management** through RPV integrity and
long-term passive heat removal; **(5) Emergency Response** which can be
minimal for HTGRs, with reduced Emergency Planning Zones justified by
the preceding layers’ effectiveness. Multiple barriers must fail
simultaneously before any release occurs.

## 7.2 Inherent Safety Characteristics

Two physics-based mechanisms exist as the core of the safety case. A
**strongly negative temperature coefficient of reactivity** (-3.5%
mk·K<sup>-1</sup>) ensures that rising fuel temperatures suppress
fission power without any operator action, via Doppler broadening of
U-238 absorption cross-sections. The **graphite core’s large thermal
inertia** (~55 tonnes, ~720 J·kg<sup>-1</sup>·K<sup>-1</sup>) causes
transients to evolve over days. Both were experimentally confirmed
during JAEA’s HTTR LOFC demonstrations.

## 7.3 TRISO Fuel and Passive Cooling

TRISO fuel particles provide four independent barriers to fission
product release: porous carbon buffer, inner PyC, SiC, and outer PyC
layers. The SiC coating retains fission products up to the 1,600°C
design limit, verified by the German AVR, US AGR, and Chinese HTR-PM
irradiation programmes. Decay heat is removed by a passive RCCS:
natural-convection air cooling around the RPV requiring no pumps,
valves, or AC power supply. This passive architecture satisfies the
project’s water-independent heat rejection requirement.

## 7.4 Safety Transient Analyses

Three transient models were developed in Python to quantify safety
margins under accident conditions. Each couples a lumped-parameter
thermal model with point kinetics and the Wigner-Way decay heat
approximation (7% of full power at shutdown, declining per ANS 5.1).
Provenance labels are applied below for each quantitative claim.

### 7.4.1. Pressurised Loss of Forced Cooling (P-LOFC)

This bounding conservative case assumes helium remains in the primary
circuit, no active SCRAM, and no natural convection. Peak fuel
temperature reaches **1579 C at 38 hours** (Figure 7.1), **21 C** below
the TRISO limit, before passively declining **[External-workstream
model result]**. This is discussed in relation to HTTR LOFC literature
and JAEA 2024 demonstration reports **[Literature]**. Omitting natural
convection ensures the prediction is conservative.

<img src="reports/final/source/media/image25.png"
style="width:6.26772in;height:3.875in" />

\[Figure 7.1. P-LOFC Transient: Peak Fuel Temperature vs. Time\]

### 7.4.2 Depressurised Loss of Forced Cooling (D-LOFC)

The D-LOFC model adds primary circuit depressurisation, eliminating
helium buoyancy-driven cooling. Heat removal relies solely on graphite
conduction and radiation to the RCCS. Peak fuel temperature reaches
**1590 C at 40 hours** (Figure 7.2), confirming fuel integrity is
maintained even under this more severe scenario **[External-workstream
model result]**.

<img src="reports/final/source/media/image27.png"
style="width:6.26772in;height:3.875in" />

\[Figure 7.2. D-LOFC Transient: Peak Fuel Temperature vs. Time\]

### 7.4.3 Natural Circulation Verification

To quantify the conservatism of Section 7.4.1, the P-LOFC model was
re-run with natural circulation included (literature-based helium flow
at ~3% of forced rate). Peak fuel temperature reduces to **1376 C**
(Figure 7.3), demonstrating **203 C** of additional margin and
confirming that the P-LOFC bounding case is appropriately conservative
**[External-workstream model result]**.

<img src="reports/final/source/media/image22.png"
style="width:6.26772in;height:3.875in" />

\[Figure 7.3. P-LOFC with Natural Circulation: Temperature Comparison\]

# Section 8: Challenges, Lessons Learned & Team Structure

## 8.1 Professional Challenges

The principal professional challenge was coordinating a genuinely
multi-disciplinary team across reactor physics, thermodynamics, chemical
engineering, and carbon accounting - each workstream operating under
different modelling frameworks, timelines, and technical languages.
Early in the project, it became clear that without a structured
mechanism for cross-workstream alignment, assumptions made in one domain
could silently invalidate work in another.

The response was twofold. First, a Master Assumptions Log was
established as a single, version-controlled record of every major input,
its source, its justification, and its sensitivity classification. Over
100 parameters were documented in this way, ensuring full traceability
and reproducibility. A concrete example of this process in action was
the boundary and headline lock to `S2_30MW_FUELDISP` with
`fuel_displacement` accounting: once fixed, all FoM tables, canonical
comparisons, and narrative claims were synchronized to a single source
of truth. Second, a RACI framework was adopted to define clear
ownership across the nuclear island, power cycle, DAC/HTSE, and CO₂
accounting workstreams - eliminating gaps and preventing duplication.

The key lesson was that rigorous documentation and communication
infrastructure are not administrative overhead - they are engineering
deliverables in their own right. In a systems-level project, the
integration layer is where designs succeed or fail.

## 8.2 Technical Challenges

The most significant technical challenge was the non-linear behaviour of
the sCO₂ Brayton cycle solver near the CO₂ critical point, where
specific heat capacity varies by a factor of five across a narrow
pressure-temperature window. Standard fixed-point iteration diverged
under these conditions, and property discontinuities propagated errors
across the coupled heat exchanger network.

The solution was a modular, staged validation approach: each component -
turbine, compressors, recuperators, dry cooler - was verified in
isolation against hand calculations before integration. The nested
fixed-point iteration architecture was then built around this validated
component library, with 11 embedded feasibility constraints checked at
every iteration rather than post-hoc. Energy closure across the full
cycle was confirmed to within 0.1%.

The lesson was that robust modelling is not a function of data quality
alone - it is a function of structured simplification, transparent
assumptions, and systematic uncertainty management. A model that
converges confidently within defined bounds is more valuable than one
that reaches a precise answer through opaque means.

## 8.3 Team Structure 

The team comprised six members: Ariella Morris, Eima Miyasaka, Mathias
Tidball, Prim Mangkhalathanakun, Stefanos Ioannidis, and Adithya Mendis.
Responsibilities were divided by technical workstream with defined
ownership: nuclear safety and transient modelling (Eima), power cycle
modelling and V&V (Stef), CO₂ accounting and primary FOM (Prim),
down-selection and system architecture (Mathias), results and secondary
FOMs (Adithya), and report structure, team coordination, and Group
Leader (Ariella). Weekly structured synchronisation meetings maintained
alignment across workstreams, with the Master Assumptions Log serving as
the shared technical ground truth. Responsibilities were distributed
among all six members to reflect the genuine collaborative nature of the
work.

# Section 9 - Novelty and Future Work

## 9.1 Novelty

The project novelty is not a single component, but the integrated use of
heat quality across the full plant: power generation at high-grade heat,
process duty at lower-grade heat, and explicit feasibility-gated
operation under dry-cooling constraints. This design framing converts
the dry-cooling penalty from a pure loss into a system-integration
opportunity while keeping headline CO2 claims tied to an explicitly
labeled comparator boundary (`fuel_displacement`) and an allocation
policy that enforces fuel-factory behavior.

## 9.2 Future Work

Priority next steps are:

1. branch-reproducible safety transient coupling in the main plant
   repository,
2. stabilization of fully coupled-cooler sensitivity mode at high
   ambient conditions,
3. expanded uncertainty campaign consistent with full BEPU framing,
4. higher-fidelity off-design heat-rejection analysis.

# Assumptions and Limitations (Main-Body Summary)

| Item | Current treatment | Why acceptable now | Next-step upgrade |
|---|---|---|---|
| Headline accounting boundary | `fuel_displacement` project FoM | Aligns with fuel-factory concept and is explicitly labeled | Add RR-specified boundary preference if provided |
| Cooling representation in headline | `fixed_boundary` | HTGR-only scope, thermodynamic closure maintained | Improve coupled cooling fidelity in sensitivity appendix |
| Reactor-side fidelity | Boundary-condition thermal source | Appropriate for this cycle scope | Add higher-fidelity reactor-side coupling |
| UQ depth | Seeded 40-sample campaign | Reproducible and schedule-compatible | Expand sample size and input uncertainty space |
| Safety integration | External workstream evidence | Preserves traceability and avoids overclaiming integration | Add tighter coupling path in future stage |

# References

(Section 1)

Sharmina, M., Edelenbosch, O. Y., Wilson, C., Freeman, R., Gernaat, D.
E. H. J., Gilbert, P., … Le Quéré, C. (2021). Decarbonising the critical
sectors of aviation, shipping, road freight and industry to limit
warming to 1.5–2°C. *Climate Policy*, *21*(4), 455–474.
https://doi.org/10.1080/14693062.2020.1831430

(For Section 7)

\[1\] International Atomic Energy Agency (1996) Defence in Depth in
Nuclear Safety. INSAG-10. Vienna: IAEA.

\[2\] Japan Atomic Energy Agency (2024) Success of Safety Demonstration
Test in HTTR \[Press release\]. 28 March. Available at:
[<u>https://www.jaea.go.jp/english/news/press/2024/032801/</u>](https://www.jaea.go.jp/english/news/press/2024/032801/)
(Accessed: 20 February 2026).

\[3\] Takamatsu, K., Tochio, D., Nakagawa, S. and Takada, S. (2014)
'Experiments and validation analyses of HTTR on loss of forced cooling
under 30% reactor power', Journal of Nuclear Science and Technology,
51(11–12). doi:10.1080/00223131.2014.967324.

\[4\] Organisation for Economic Co-operation and Development/Nuclear
Energy Agency (2024) Loss of Forced Coolant (LOFC) Project. Available
at:
[<u>https://www.oecd-nea.org/jcms/pl_25168</u>](https://www.oecd-nea.org/jcms/pl_25168)
(Accessed: 24 February 2026).

\[5\] Idaho National Laboratory (no date) TRISO Fuel: Accident
Performance and NRC Engagement. Report Sort_66160. Available at:
[<u>https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_66160.pdf</u>](https://inldigitallibrary.inl.gov/sites/sti/sti/Sort_66160.pdf)
(Accessed: 24 February 2026).

\[6\] International Atomic Energy Agency (2003) Evaluation of High
Temperature Gas Cooled Reactor Performance. TECDOC-1382. Vienna: IAEA.

\[7\] American Nuclear Society (2014) Decay Heat Power in Light Water
Reactors. ANS 5.1-2014. La Grange Park, IL: ANS.

\[8\] Generation IV International Forum (2018) VHTR Safety Assessment.
GIF/VHTR. Available at:
[<u>https://www.gen-4.org/gif/upload/docs/application/pdf/2018-12/gifvhtr_safety_assessment_finaldec2018.pdf</u>](https://www.gen-4.org/gif/upload/docs/application/pdf/2018-12/gifvhtr_safety_assessment_finaldec2018.pdf)
(Accessed: 24 February 2026).

(For Sections 4.3, 6.2, and Appendix 4.3)

> EUROCONTROL. (n.d.). *7 Amount of emissions released by fuel burn*.
> EUROCONTROL. Retrieved
> [<u>https://ansperformance.eu/economics/cba/standard-inputs/latest/chapters/amount_of_emissions_released_by_fuel_burn.html</u>](https://ansperformance.eu/economics/cba/standard-inputs/latest/chapters/amount_of_emissions_released_by_fuel_burn.html)
>
> ICAP. (2026, January 19). *EU Emissions Trading System (EU ETS) \|
> International Carbon Action Partnership*.
> [<u>https://icapcarbonaction.com/en/ets/eu-emissions-trading-system-eu-ets</u>](https://icapcarbonaction.com/en/ets/eu-emissions-trading-system-eu-ets)
>
> Le Boulch, D., Buronfosse, M., Le Guern, Y., Duvernois, P.-A., &
> Payen, N. (2024). Meta-analysis of the greenhouse gases emissions of
> nuclear electricity generation: Learnings for process-based LCA. *The
> International Journal of Life Cycle Assessment*, *29*(5), 857–872.
> [<u>https://doi.org/10.1007/s11367-024-02293-y</u>](https://doi.org/10.1007/s11367-024-02293-y)
>
> MissionZero. (n.d.). *Sustainable CO2: What it is, where it comes
> from, what it means for the climate*. Retrieved 19 January 2026, from
> [<u>https://www.missionzero.tech/lab-notes/sustainable-co2</u>](https://www.missionzero.tech/lab-notes/sustainable-co2)
>
> Rolls-Royce Corporation. (2021, October). *FAA Continuous Lower
> Energy, Emissions, and Noise (CLEEN II) Technologies Program*.
> [<u>https://www.faa.gov/sites/faa.gov/files/2022-02/phase2_rolls-royce_sustainable_aviation_fuels_final.pdf</u>](https://www.faa.gov/sites/faa.gov/files/2022-02/phase2_rolls-royce_sustainable_aviation_fuels_final.pdf)
>
> Scott, D. (2025, October 6). Why SAF is expected to play a larger role
> in near- and medium-term decarbonization than zero-emission aircraft.
> *International Council on Clean Transportation*.
> [<u>https://theicct.org/why-saf-is-expected-to-have-a-larger-role-in-near-and-medium-term-decarbonization-than-zero-emission-aircraft-sept25/</u>](https://theicct.org/why-saf-is-expected-to-have-a-larger-role-in-near-and-medium-term-decarbonization-than-zero-emission-aircraft-sept25/)

# Appendix

## Appendix 4.3: Detailed CO<sub>2</sub> Calculation and Derivations

**Sensitivity-only note:** this appendix is provided for
legacy equation continuity and comparator context. In this final report,
`fuel_displacement` is the headline basis and `operational_only` is a
sensitivity basis.

**Symbol mapping to current report boundary labels:**
- Legacy `E_Baseline` and `E_Project` terms map to comparator
  accounting in `fuel_displacement` headline mode.
- Main-body sensitivity uses
  `Net_CO2_operational_only = CO2_DAC + CO2_grid`.
- Legacy net result (`~33,374 tCO2/year`) is historical comparator
  context and not the current solved headline value.

Table 4.3: Input parameters and numerical substitutions

<table style="width:97%;">
<colgroup>
<col style="width: 19%" />
<col style="width: 19%" />
<col style="width: 19%" />
<col style="width: 15%" />
<col style="width: 23%" />
</colgroup>
<thead>
<tr>
<th style="text-align: center;"><strong>Parameter</strong></th>
<th style="text-align: center;"><strong>Symbol</strong></th>
<th style="text-align: center;"><strong>Value</strong></th>
<th style="text-align: center;"><strong>Unit</strong></th>
<th style="text-align: center;"><strong>Source</strong></th>
</tr>
<tr>
<th colspan="5" style="text-align: center;"><p><strong>Baseline
Emissions</strong></p>
<p><img src="reports/final/source/media/image7.png"
style="width:3.38889in;height:0.875in"
alt="{&quot;code&quot;:&quot;\\begin{align*}\n{\\left(1\\right)\\,E_{\\text{Baseline}}}&amp;={m_{\\text{Jet}\\;\\text{A-1,}\\;\\text{comb.}}\\times EF_{\\text{Jet}\\;\\text{A-1,}\\;\\text{comb.}}}\\\\\n{\\,}&amp;={10596000\\times3.15}\\\\\n{\\,}&amp;={33377400\\,\\text{kgCO}_{2}/\\text{year}}\\\\\n{\\,}&amp;\\approx{33377.40\\,\\text{tCO}_{2}/\\text{year}}\t\n\\end{align*}&quot;,&quot;type&quot;:&quot;align*&quot;,&quot;aid&quot;:null,&quot;font&quot;:{&quot;family&quot;:&quot;Arial&quot;,&quot;color&quot;:&quot;#000000&quot;,&quot;size&quot;:11},&quot;id&quot;:&quot;3-1&quot;,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;backgroundColorModified&quot;:false,&quot;ts&quot;:1772377513939,&quot;cs&quot;:&quot;pAZuE4r3AtZHHpi1S4kw5w==&quot;,&quot;size&quot;:{&quot;width&quot;:325,&quot;height&quot;:84}}" /></p></th>
</tr>
<tr>
<th>Annual Jet A-1 mass</th>
<th><img src="reports/final/source/media/image8.png"
style="width:0.56944in"
alt="{&quot;code&quot;:&quot;\\begin{lalign*}\n&amp;{m_{\\text{Jet}\\;\\text{A-1}}\\;}\t\n\\end{lalign*}&quot;,&quot;aid&quot;:null,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;id&quot;:&quot;4&quot;,&quot;backgroundColorModified&quot;:false,&quot;type&quot;:&quot;lalign*&quot;,&quot;font&quot;:{&quot;size&quot;:11,&quot;color&quot;:&quot;#000000&quot;,&quot;family&quot;:&quot;Arial&quot;},&quot;ts&quot;:1772370255728,&quot;cs&quot;:&quot;mQwlEO0X2bbA8Hm8PpQUtg==&quot;,&quot;size&quot;:{&quot;width&quot;:54,&quot;height&quot;:9}}" /></th>
<th>10,596,000</th>
<th>kg/year</th>
<th>Derived</th>
</tr>
<tr>
<th>Jet A-1 emission factor</th>
<th><img src="reports/final/source/media/image17.png"
style="width:0.65278in;height:0.13889in"
alt="{&quot;font&quot;:{&quot;size&quot;:11,&quot;color&quot;:&quot;#000000&quot;,&quot;family&quot;:&quot;Arial&quot;},&quot;type&quot;:&quot;$$&quot;,&quot;id&quot;:&quot;5&quot;,&quot;aid&quot;:null,&quot;backgroundColorModified&quot;:false,&quot;code&quot;:&quot;$$EF_{\\text{Jet}\\;\\text{A-1}}$$&quot;,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;ts&quot;:1772370445547,&quot;cs&quot;:&quot;TEMQwohJqude449lmmQCQA==&quot;,&quot;size&quot;:{&quot;width&quot;:62,&quot;height&quot;:13}}" /></th>
<th>3.15</th>
<th>kgCO₂/kg</th>
<th>(EUROCONTROL, n.d.)</th>
</tr>
<tr>
<th colspan="5" style="text-align: center;"><p><strong>Project
Emissions</strong></p>
<p><img src="reports/final/source/media/image18.png"
style="width:5.25in;height:0.875in"
alt="{&quot;type&quot;:&quot;align*&quot;,&quot;id&quot;:&quot;2-1&quot;,&quot;backgroundColorModified&quot;:false,&quot;font&quot;:{&quot;size&quot;:11,&quot;color&quot;:&quot;#000000&quot;,&quot;family&quot;:&quot;Arial&quot;},&quot;code&quot;:&quot;\\begin{align*}\n{\\left(2\\right)\\;E_{\\text{Project}}}&amp;={\\,\\left(Q_{\\text{Total,}\\;\\text{elec.}}\\times EF_{\\text{Nuc.,}\\;\\text{elec.}}\\right)+\\left(Q_{\\text{Total,}\\;\\text{heat}}\\times EF_{\\text{Nuc.,}\\;\\text{heat}}\\right)}\\\\\n{\\,}&amp;={\\left(431.41\\times 1.767\\right)+\\left(640.81\\times 4.38\\right)}\\\\\n{\\,}&amp;\\approx{3570.62\\,\\text{kgCO}_{2}/\\text{year}}\\\\\n{\\,}&amp;\\approx{3.57\\,\\text{tCO}_{2}/\\text{year}}\t\n\\end{align*}&quot;,&quot;aid&quot;:null,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;ts&quot;:1772378254416,&quot;cs&quot;:&quot;H8GpKS7pKQXgNP01WuR9TA==&quot;,&quot;size&quot;:{&quot;width&quot;:504,&quot;height&quot;:84}}" /></p></th>
</tr>
<tr>
<th>Total electrical energy demand</th>
<th><img src="reports/final/source/media/image10.png"
style="width:0.75in;height:0.16667in"
alt="{&quot;type&quot;:&quot;$$&quot;,&quot;font&quot;:{&quot;color&quot;:&quot;#000000&quot;,&quot;family&quot;:&quot;Arial&quot;,&quot;size&quot;:11},&quot;code&quot;:&quot;$$Q_{\\text{Total,}\\;\\text{elec.}}$$&quot;,&quot;id&quot;:&quot;7&quot;,&quot;backgroundColorModified&quot;:false,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;aid&quot;:null,&quot;ts&quot;:1772370723405,&quot;cs&quot;:&quot;zlLCeUe3+JJNcgUC6AQALw==&quot;,&quot;size&quot;:{&quot;width&quot;:72,&quot;height&quot;:16}}" /></th>
<th>431.41</th>
<th>TJ/year</th>
<th>Derived</th>
</tr>
<tr>
<th>Total heat energy demand</th>
<th><img src="reports/final/source/media/image1.png"
style="width:0.75in;height:0.16667in"
alt="{&quot;code&quot;:&quot;$$Q_{\\text{Total,}\\;\\text{heat}}$$&quot;,&quot;backgroundColorModified&quot;:false,&quot;font&quot;:{&quot;color&quot;:&quot;#000000&quot;,&quot;family&quot;:&quot;Arial&quot;,&quot;size&quot;:11},&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;type&quot;:&quot;$$&quot;,&quot;id&quot;:&quot;8&quot;,&quot;aid&quot;:null,&quot;ts&quot;:1772370772269,&quot;cs&quot;:&quot;GHC1Ynnt/UwU8tlXg0LPfQ==&quot;,&quot;size&quot;:{&quot;width&quot;:72,&quot;height&quot;:16}}" /></th>
<th>640.81</th>
<th>TJ/year</th>
<th>Derived</th>
</tr>
<tr>
<th>Nuclear electricity EF</th>
<th><img src="reports/final/source/media/image13.png"
style="width:0.81944in;height:0.16667in"
alt="{&quot;code&quot;:&quot;$$EF_{\\text{Nuc.,}\\;\\text{elec.}}$$&quot;,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;aid&quot;:null,&quot;backgroundColorModified&quot;:false,&quot;type&quot;:&quot;$$&quot;,&quot;font&quot;:{&quot;family&quot;:&quot;Arial&quot;,&quot;color&quot;:&quot;#000000&quot;,&quot;size&quot;:11},&quot;id&quot;:&quot;9&quot;,&quot;ts&quot;:1772370801348,&quot;cs&quot;:&quot;nSJ2dmOYtR5k0sntv/EPbg==&quot;,&quot;size&quot;:{&quot;width&quot;:78,&quot;height&quot;:16}}" /></th>
<th>1.767</th>
<th>kgCO₂/TJ</th>
<th>(Le Boulch et al., 2024)</th>
</tr>
<tr>
<th>HTGR efficiency</th>
<th><img src="reports/final/source/media/image2.png"
style="width:1.04167in;height:0.11111in"
alt="{&quot;aid&quot;:null,&quot;code&quot;:&quot;$$\\eta_{\\text{HTGR,}\\;\\text{heat}\\to\\text{elec.}}$$&quot;,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;type&quot;:&quot;$$&quot;,&quot;font&quot;:{&quot;color&quot;:&quot;#000000&quot;,&quot;size&quot;:10,&quot;family&quot;:&quot;Arial&quot;},&quot;id&quot;:&quot;14&quot;,&quot;backgroundColorModified&quot;:false,&quot;ts&quot;:1772375536106,&quot;cs&quot;:&quot;TlcH+8DZFGt6/NwQELQwmw==&quot;,&quot;size&quot;:{&quot;width&quot;:100,&quot;height&quot;:10}}" /></th>
<th>40.32%</th>
<th style="text-align: center;">-</th>
<th>Derived</th>
</tr>
<tr>
<th>Nuclear heat EF</th>
<th><img src="reports/final/source/media/image11.png"
style="width:0.81944in;height:0.16667in"
alt="{&quot;type&quot;:&quot;$$&quot;,&quot;backgroundColorModified&quot;:false,&quot;id&quot;:&quot;10&quot;,&quot;code&quot;:&quot;$$EF_{\\text{Nuc.,}\\;\\text{heat}}$$&quot;,&quot;font&quot;:{&quot;color&quot;:&quot;#000000&quot;,&quot;size&quot;:11,&quot;family&quot;:&quot;Arial&quot;},&quot;aid&quot;:null,&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;ts&quot;:1772370824419,&quot;cs&quot;:&quot;MJlvjZs5doJ4ipNSOXlUYA==&quot;,&quot;size&quot;:{&quot;width&quot;:78,&quot;height&quot;:16}}" /></th>
<th>4.38</th>
<th>kgCO₂/TJ</th>
<th>Derived</th>
</tr>
<tr>
<th colspan="5" style="text-align: center;"><p><strong>Net
CO<sub>2</sub> Reduction</strong></p>
<p><img src="reports/final/source/media/image23.png"
style="width:3.375in;height:0.63889in"
alt="{&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;backgroundColorModified&quot;:false,&quot;code&quot;:&quot;\\begin{align*}\n{\\left(3\\right)\\;\\text{Net}\\;\\text{CO}_{2}\\;\\text{Reduction}}&amp;={E_{\\text{Baseline}}-E_{\\text{Project}}}\\\\\n{\\,}&amp;={33377.40-3.57}\\\\\n{\\,}&amp;\\approx{33374\\,\\text{tCO}_{2}/\\text{year}}\t\n\\end{align*}&quot;,&quot;aid&quot;:null,&quot;id&quot;:&quot;16&quot;,&quot;font&quot;:{&quot;color&quot;:&quot;#000000&quot;,&quot;size&quot;:11,&quot;family&quot;:&quot;Arial&quot;},&quot;type&quot;:&quot;align*&quot;,&quot;ts&quot;:1772377722537,&quot;cs&quot;:&quot;fNqt75+THi/HdlbX33y0FQ==&quot;,&quot;size&quot;:{&quot;width&quot;:324,&quot;height&quot;:61}}" /></p></th>
</tr>
</thead>
<tbody>
</tbody>
</table>

#### **Derivation of Nuclear Heat EF**

The nuclear heat emission factor is derived from the nuclear electricity
emission factor and the HTGR efficiency of our model (Liu et al., 2020).

<img src="reports/final/source/media/image21.png"
style="width:2.30556in;height:1.08333in"
alt="{&quot;backgroundColorModified&quot;:false,&quot;aid&quot;:null,&quot;id&quot;:&quot;15&quot;,&quot;font&quot;:{&quot;size&quot;:11,&quot;family&quot;:&quot;Arial&quot;,&quot;color&quot;:&quot;#000000&quot;},&quot;backgroundColor&quot;:&quot;#ffffff&quot;,&quot;code&quot;:&quot;\\begin{align*}\n{EF_{\\text{Nuc.,}\\;\\text{heat}}}&amp;={\\frac{EF_{\\text{Nuc.,}\\;\\text{elec.}}}{\\eta_{\\text{HTGR,}\\;\\text{heat}\\to \\text{elec.}}}}\\\\\n{\\,}&amp;={\\frac{1.767}{0.4032}}\\\\\n{\\,}&amp;={4.38\\,\\text{kgCO}_{2}/\\text{TJ}}\t\n\\end{align*}&quot;,&quot;type&quot;:&quot;align*&quot;,&quot;ts&quot;:1772376792693,&quot;cs&quot;:&quot;7Y2bGlj4zpy/cy3AFkziKw==&quot;,&quot;size&quot;:{&quot;width&quot;:221,&quot;height&quot;:104}}" />
