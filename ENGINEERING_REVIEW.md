# Engineering Review: HTGR + sCO2 + Process Integration Model

**Review Date:** 2026-01-20
**Reviewer:** Engineering Audit (Pre-Presentation)
**Purpose:** Validate implementation against architecture specification and identify issues before Rolls-Royce presentation

---

## Executive Summary

The implementation **largely follows the corrected architecture specification** and addresses 5 of the 6 identified issues from the original spec. The model produces physically plausible results, but there are several areas requiring attention before presentation.

### Overall Assessment: **ACCEPTABLE WITH CAVEATS**

| Category | Status | Notes |
|----------|--------|-------|
| Core Physics | ✅ Sound | Enthalpy-based, real-gas properties |
| Solver Architecture | ✅ Implemented | Nested iteration with convergence |
| Heat Exchanger Models | ✅ Correct | Segmented with per-segment pinch |
| Pressure Drops | ✅ Included | Throughout cycle |
| Dry Cooler | ✅ Physical | Fan power from pressure drop |
| Process Allocation | ⚠️ Simplified | See Issue #1 below |
| Numerical Results | ⚠️ Plausible | Some values need context |

---

## Part 1: Issues Identified

### ISSUE #1: Process Allocation Energy Consistency (MODERATE)

**Problem:** The process allocation module splits `Q_reject` between DAC and dry cooler, but the dry cooler fan power was calculated assuming it handles the full `Q_reject`.

**In the code:**
```
Q_waste_available = 20.16 MW (from cycle)
Q_to_DAC = 10.08 MW
Q_to_cooler = 10.08 MW
```

**But:** Fan power (1.40 MW) was calculated for rejecting 20.16 MW, not 10.08 MW.

**Impact:** If cooler only rejects 10 MW, fan power would be lower (~0.7 MW). This means:
- Net power would increase slightly (~0.7 MW more available)
- CO2 reduction FOM would improve slightly

**Mitigation for presentation:**
- Present current results as conservative (fan power overestimated)
- State this is a first-order analysis; detailed design would iterate between cycle and process allocation

**Recommended fix:** Re-solve dry cooler with actual Q_to_cooler after allocation optimization.

---

### ISSUE #2: DAC Heat Source Physical Implementation (MINOR)

**Question for RR:** The model assumes waste heat at T_7 (190°C) can be partially diverted to DAC before the cooler. This requires:
- A heat exchanger between CO2 stream and DAC regenerator
- Or a thermal oil loop to transfer heat

**Current assumption:** 100% heat transfer efficiency from cycle waste to DAC.

**Impact:** Realistic heat transfer would reduce effective heat to DAC by 10-20%.

**For presentation:** State this as an upper bound; detailed design would include HX efficiency.

---

### ISSUE #3: CO2 Reduction Number Context (PRESENTATION RISK)

**The headline number:** 45,182 tonnes CO2/year (1,506 t/MWth/year)

**This is dominated by DAC (45,447 t/yr)**, not grid displacement (0 t/yr).

**Potential RR question:** "Why is grid export zero?"

**Answer:** The optimizer maximizes net CO2 reduction. At grid intensity of 400 g/kWh:
- 1 MWh exported avoids 0.4 tonnes CO2
- 1 MWh to DAC (via heat at 1750 kWh_th/t_CO2 equivalent) captures more CO2

The optimizer correctly chose DAC over grid export because the CO2 capture rate exceeds grid displacement rate.

**Recommendation:** Prepare sensitivity showing how result changes with different grid intensities:
- High-carbon grid (800 g/kWh): Grid export becomes attractive
- Low-carbon grid (100 g/kWh): DAC dominates

---

### ISSUE #4: Dostal Validation Shows "Infeasible" (CLARIFICATION NEEDED)

**Test output:** "Feasible: False" but "VALIDATION: PASSED"

**Explanation:** The Dostal validation case operates at 32°C compressor inlet (T_1), which is only 0.87K above CO2 critical temperature (31.13°C). This violates the 3K margin constraint but is physically valid for the benchmark comparison.

**The validation passes** because thermal efficiency (44.74%) matches Dostal's reference (45% ± 3%).

**For presentation:** Explain that Dostal's conditions are at the edge of supercritical margin; our design case (40°C ambient → 50°C T_1) has proper margins.

---

### ISSUE #5: HTR Pinch Margin is Tight (DESIGN SENSITIVITY)

**Result:** HTR pinch = 12 K (margin of 2 K above 10 K minimum)

This is the most binding constraint in the current design. Small changes in operating conditions could cause pinch violations.

**For presentation:** This indicates the recuperator sizing is aggressive. In detailed design, either:
- Increase recuperator UA (larger HX)
- Accept lower thermal efficiency
- Adjust split fraction

---

## Part 2: Validation of Numerical Results

### Cycle Performance

| Parameter | Value | Sanity Check | Status |
|-----------|-------|--------------|--------|
| Net Efficiency | 27.4% | Typical sCO2 at 500-550°C TIT: 25-35% | ✅ Reasonable |
| Thermal Efficiency | 32.5% | Lower than Dostal (45%) due to higher T_1 | ✅ Expected |
| Turbine Inlet T | 520°C | Below HTTR He outlet (850°C) by IHX approach | ✅ Correct |
| Compressor Inlet T | 50°C | 10K above 40°C ambient (approach constraint) | ✅ Correct |

### Mass Flows

| Parameter | Value | Calculation Check | Status |
|-----------|-------|-------------------|--------|
| CO2 flow | 161.3 kg/s | Q_in / Δh = 30MW / ~186 kJ/kg ≈ 161 kg/s | ✅ Correct |
| He flow | 12.7 kg/s | Q_th / (cp × ΔT) = 30MW / (5.2 × 455) ≈ 12.7 kg/s | ✅ Correct |

### Energy Balance

| Component | Value (MW) |
|-----------|------------|
| Q_thermal (in) | 30.00 |
| W_gross | 9.71 |
| W_fan | 1.40 |
| W_aux | 0.10 |
| W_net | 8.21 |
| Q_reject | 20.16 |
| **Sum out** | **29.87** |
| **Residual** | **0.13 MW (0.4%)** |

Energy closure is within 1% - acceptable for engineering analysis.

### CO2 Production Numbers

| Process | Value | Calculation Verification |
|---------|-------|-------------------------|
| H2 production | 512 t/yr | 2.44 MW × 8760h × 0.9 / 37.5 kWh/kg = 513 t/yr ✅ |
| CO2 capture (DAC) | 45,447 t/yr | 10.08 MW × 8760h × 0.9 / (1.75 MWh/t) = 45,446 t/yr ✅ |
| Methanol | 2,651 t/yr | Limited by H2: 512t / 0.1875 × 0.97 = 2,648 t/yr ✅ |

All production calculations are mathematically correct.

---

## Part 3: Compliance with Architecture Specification

### Six Corrected Issues - Implementation Status

| Issue | Description | Status | Evidence |
|-------|-------------|--------|----------|
| #1 | Enthalpy-based segmented HX | ✅ Implemented | `hx/segmented_hx.py` uses h_func_hot/cold |
| #2 | Pressure drops throughout | ✅ Implemented | dP_hot, dP_cold in all HX, cycle accounts for drops |
| #3 | IHX-cycle coupled solve | ✅ Implemented | `coupled_solver.py` iterates T_5 with IHX |
| #4 | Physical dry cooler parasitics | ✅ Implemented | W_fan = V_dot × dP / η (not constant factor) |
| #5 | Constrained allocation | ⚠️ Partial | Optimization works, but not iterated with cycle |
| #6 | Embedded feasibility | ✅ Implemented | Constraints checked during solve, not post-hoc |

### Constraint Mapping

| Spec Constraint | Implementation | Verified |
|-----------------|----------------|----------|
| T01: T_1 > T_crit + margin | `sco2_cycle.py:248` | ✅ |
| T02: P_low > P_crit + margin | `sco2_cycle.py:249` | ✅ |
| T03: T_TIT ≤ T_max | `sco2_cycle.py:263` | ✅ |
| P01-P04: Pinch constraints | `segmented_hx.py:224-235` | ✅ |
| E01-E03: Energy constraints | `sco2_cycle.py:441-457` | ✅ |

---

## Feasibility-Recovery Hierarchy (Current Implementation)

The headline fixed-boundary solve now applies deterministic feasibility recovery in staged order, while keeping core physics constraints unchanged.

### Stage Order

1. Operating-point search only
   - bounded search over `(P_high, P_low, f_recomp)` with deterministic coarse + local refinement.
2. Add `T_1_boundary_target` sweep
3. Add `IHX dT_approach` sweep
4. Add `cooling_aux_fraction` sweep

### Allowed Moderate Tuning Ranges

- `T_1_boundary_target`: `[T_ambient + 8 K, T_ambient + 12 K]`
- `IHX dT_approach`: `[25 K, 35 K]`
- `cooling_aux_fraction`: `[0.005, 0.02]`

Selected operating point and tuned assumptions are persisted into scenario metadata for traceability.

### Gate Behavior

- Headline infeasible with no override: fail-fast before CO2/canonical stages.
- Override: `ALLOW_INFEASIBLE_DIAGNOSTIC=1` permits diagnostic continuation.
- Canonical generation: `require_feasible=True` aborts and writes `outputs/canonical_pack/feasibility_failure_report.json` when any scenario is infeasible.

---

## Part 4: Presentation Preparation

### Key Messages for Rolls-Royce

1. **Primary FOM Delivered:** 1,506 t_CO2/MWth/year net reduction
   - Dominated by DAC capture using waste heat at 190°C
   - Hydrogen production enables methanol synthesis as carbon sink

2. **Modelling Approach Strengths:**
   - Real-gas properties throughout (CoolProp)
   - Segmented HX with per-segment pinch checks
   - Physical fan power model (not arbitrary factor)
   - Embedded feasibility constraints

3. **Validated Against Literature:**
   - Dostal (2004) sCO2 cycle: 44.74% vs 45% ± 3% reference

4. **Water-Independent Heat Rejection:**
   - Dry cooler with finned-tube bank
   - Parasitic load: 6.9% of rejected heat
   - Physical model based on Kays & London correlations

### Anticipated Questions and Answers

**Q: Why is cycle efficiency only 32.5%, not the ~45% often cited for sCO2?**
A: The often-cited 45% is for optimized conditions (32°C compressor inlet, 550°C TIT). Our design operates at 50°C compressor inlet (required for 40°C ambient with air cooling) and 520°C TIT (IHX approach from 850°C He). These realistic constraints reduce efficiency.

**Q: How confident are you in the DAC numbers?**
A: The heat intensity (1750 kWh_th/t_CO2) is based on Climeworks solid sorbent technology. This is a literature-based parameter; actual performance depends on specific DAC design and integration. We used mid-range values from published sources.

**Q: What's the biggest uncertainty?**
A: The HX pinch constraints, particularly HTR, are binding. Detailed thermal-hydraulic design is needed to confirm the recuperator can achieve the required effectiveness without pinch violation.

**Q: Can you scale this to larger reactors?**
A: Yes. The 30 MWth HTTR-based design can be scaled. For n parallel cores, multiply all outputs by n. The FOM (t_CO2/MWth/year) remains constant at ~1,500.

---

## Part 5: Recommended Pre-Presentation Actions

### Must Do (Before Presentation)
1. ✅ Review this document
2. ⬜ Prepare slide with energy flow Sankey diagram
3. ⬜ Prepare slide showing T-s diagram with state points
4. ⬜ Prepare sensitivity: CO2 reduction vs grid intensity

### Should Do (If Time Permits)
1. ⬜ Re-run with Q_to_cooler (not full Q_reject) for fan power
2. ⬜ Add sensitivity: ambient temperature effect on efficiency
3. ⬜ Document assumption ranges with literature references

### Code Quality Notes
- Code follows PEP8 style guidelines
- Modular structure with clear separation of concerns
- Comprehensive docstrings on all classes and functions
- Results exported to JSON for reproducibility

---

## Conclusion

The model is **ready for presentation** with the understanding that:

1. The CO2 reduction FOM (1,506 t/MWth/year) is a **first-order estimate** that would be refined in detailed design
2. The approach is **physically sound** and follows the corrected architecture
3. Some **conservative assumptions** (fan power) mean actual performance may be slightly better
4. The **tight HTR pinch margin** indicates this is an optimistic design point that needs thermal-hydraulic validation

The team can present these results with confidence, provided the caveats are clearly communicated.
